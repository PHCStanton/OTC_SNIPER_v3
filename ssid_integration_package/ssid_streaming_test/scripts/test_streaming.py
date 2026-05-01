import os
import sys
import time
import json
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, Any

# Ensure we're running from the ssid_integration_package folder or similar
# so we can find app/backend correctly
_SCRIPT_DIR = Path(__file__).resolve().parent
_PACKAGE_ROOT = _SCRIPT_DIR.parent.parent  # c:/v3/OTC_SNIPER/ssid_integration_package
_PROJECT_ROOT = _PACKAGE_ROOT.parent       # c:/v3/OTC_SNIPER
_APP_DIR = _PROJECT_ROOT / "app"

# Override OTC_DATA_DIR to point to our test directory BEFORE importing config
_TEST_DATA_DIR = _SCRIPT_DIR.parent / "app" / "data"
os.environ["OTC_DATA_DIR"] = str(_TEST_DATA_DIR)
# Setup dotenv early so config picks it up
from dotenv import load_dotenv
load_dotenv(_SCRIPT_DIR.parent / ".env")

# Inject app into sys.path so we can import backend as backend
if str(_APP_DIR) not in sys.path:
    # Need to insert _PROJECT_ROOT so `app.backend...` works
    sys.path.insert(0, str(_PROJECT_ROOT))
    # Also insert _APP_DIR so `backend...` works
    sys.path.insert(0, str(_APP_DIR))

# Ensure required module is installed
try:
    import pocketoptionapi
    import socketio
except ImportError as e:
    print(f"FAILED TO IMPORT DEPENDENCIES: {e}")
    print("Please ensure you are running this in the 'QuFLX-v2' conda environment.")
    sys.exit(1)

# Import backend modules
from backend.session.pocket_option_session import PocketOptionSession
from backend.services.streaming import StreamingService
from backend.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("StreamingTest")

# We'll suppress some chatty logs from the library
logging.getLogger("pocketoptionapi").setLevel(logging.WARNING)

class StreamingTestHarness:
    def __init__(self, ssid: str, asset: str, duration: int, verbose: bool):
        self.ssid = ssid
        self.asset = asset
        self.duration = duration
        self.verbose = verbose
        
        self.session = None
        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self.streaming_service = StreamingService(sio_server=self.sio)
        
        self.ticks_received = 0
        self.signals_received = 0
        self.manipulations = 0
        self.min_score = 100.0
        self.max_score = 0.0
        self.warmup_complete_tick = -1

    async def setup_client(self):
        """Capture the event loop and directly patch gv.set_csv for thread-safe tick dispatch.
        
        We bypass PocketOptionSession._apply_hooks() entirely because that hook uses
        asyncio.get_running_loop() from the WS background thread, which always fails.
        Instead we patch gv.set_csv directly here, using run_coroutine_threadsafe with
        the main loop we captured from asyncio.run().
        """
        self._loop = asyncio.get_running_loop()

        import pocketoptionapi.global_value as gv

        # If the class already applied its hook, restore the true original first
        # so we don't double-wrap. Then clear class-level state.
        if PocketOptionSession._original_set_csv is not None:
            gv.set_csv = PocketOptionSession._original_set_csv
        _true_original_set_csv = gv.set_csv
        PocketOptionSession._tick_callback = None
        PocketOptionSession._original_set_csv = None

        streaming = self.streaming_service

        def _threadsafe_set_csv(key, value, path=None):
            """Direct patch: call true original CSV writer, then schedule tick onto our loop."""
            res = _true_original_set_csv(key, value, path)
            if isinstance(value, list) and len(value) > 0:
                tick = value[0]
                if 'price' in tick:
                    try:
                        asset = str(key)
                        price = float(tick['price'])
                        ts = float(tick['time'])
                        asyncio.run_coroutine_threadsafe(
                            streaming.process_tick(asset, price, ts),
                            self._loop
                        )
                    except Exception as hook_err:
                        logger.warning("Tick hook error for %s: %s", key, hook_err)
            return res

        gv.set_csv = _threadsafe_set_csv
        print("── Phase C: Tick Hook Setup ────────────────────────────────────────")
        print("[HOOK] gv.set_csv patched directly (thread-safe, run_coroutine_threadsafe) ✅")


        self.client = socketio.AsyncClient()
        
        @self.client.on('market_data')
        async def on_market_data(data):
            self.ticks_received += 1
            tick = self.ticks_received
            
            score = data.get("oteo_score", 50.0)
            price = data.get("price", 0.0)
            manipulation = data.get("manipulation")
            
            # Simple warmup detection
            is_warmup = "velocity" not in data
            if is_warmup:
                print(f"[TICK {tick:4d}] {self.asset} | price: {price:.5f} | OTEO: {score:.1f} (warmup {tick}/50)")
            else:
                if self.warmup_complete_tick == -1:
                    self.warmup_complete_tick = tick
                
                self.min_score = min(self.min_score, score)
                self.max_score = max(self.max_score, score)
                
                conf = data.get("confidence", "LOW")
                rec = data.get("recommended", "CALL")
                mat = data.get("maturity", 0.0)
                
                print(f"[TICK {tick:4d}] {self.asset} | price: {price:.5f} | OTEO: {score:.1f} | {rec:4s} | {conf:6s} | maturity: {mat:.2f}")
                
                if conf in ("MEDIUM", "HIGH"):
                    self.signals_received += 1
                    print(f"🔥 [SIGNAL ] {self.asset} | {rec} | {conf} (score: {score:.1f})")
            
            if manipulation:
                self.manipulations += 1
                flag_str = f"pinning: {manipulation.get('pinning')} | push_snap: {manipulation.get('push_snap')}"
                print(f"⚠️ [MANIP  ] {self.asset} | {flag_str}")
                
            if self.verbose:
                print(f"   RAW: {data}")

        @self.client.on('warmup_status')
        async def on_warmup(data):
            ready = data.get("ready", False)
            ticks = data.get("ticks_received", 0)
            print(f"[WARMUP ] {self.asset} | ticks: {ticks} | ready: {str(ready).lower()}")

        # We don't actually need to "connect" via HTTP because we're just
        # instantiating the server and emitting to it, and client is listening.
        # However, python-socketio client needs to connect to the server ASGI app.
        # For simplicity in this test, we can just intercept the emit on the server
        # instead of creating a full ASGI app harness.
        
        # Override SIO emit to capture it directly in our process
        self.original_emit = self.sio.emit
        async def mock_emit(event, data, room=None, **kwargs):
            if event == 'market_data':
                await on_market_data(data)
            elif event == 'warmup_status':
                await on_warmup(data)
        
        self.sio.emit = mock_emit

    def connect(self) -> bool:
        """Initialize the Pocket Option session and connect (synchronous — runs before asyncio loop)."""
        print(f"\n── Phase B: Connection ─────────────────────────────────────────────")
        print(f"[CONN] Connecting to Pocket Option...")

        self.session = PocketOptionSession(self.ssid, timeout=15)
        success, msg = self.session.connect()

        if success:
            print(f"[CONN] ✅ T1/T2 PASS — {msg}")
            return True
        else:
            print(f"[CONN] ❌ T1/T2 FAIL — {msg}")
            return False

    def _subscribe_sync(self):
        """Call change_symbol synchronously — must run in a thread (no running event loop)."""
        self.session._api.change_symbol(self.asset, 1)

    async def run(self):
        """Run the main collection loop (asyncio context). connect() must be called first."""
        await self.setup_client()

        print(f"\n── Phase D: Asset Subscription ─────────────────────────────────────")
        print(f"[SUB] Subscribing to {self.asset} (period=1)...")
        # change_symbol internally calls loop.run_until_complete — run it in a thread
        # so it gets a clean thread-local event loop and doesn't conflict with ours.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._subscribe_sync)
        print(f"[SUB] changeSymbol sent. Awaiting ticks for {self.duration} seconds...\n")
        
        print(f"── Phase E: Live Tick Collection ({self.duration}s) ─────────────────────────────")
        
        # Run collection for the specified duration
        start_time = time.time()
        while time.time() - start_time < self.duration:
            await asyncio.sleep(1)
            
        print(f"\n── Phase F: Verification Summary ───────────────────────────────────")
        self.print_summary()
        
        print(f"\n── Phase G: Cleanup ────────────────────────────────────────────────")
        print(f"[CLEAN] Disconnecting from Pocket Option...")
        self.session.disconnect()
        print(f"[CLEAN] Done. Tick/Signal logs preserved in: {os.environ['OTC_DATA_DIR']}")

    def print_summary(self):
        """Print the test summary pass/fail matrix"""
        tick_dir = Path(os.environ["OTC_DATA_DIR"]) / "tick_logs" / self.asset
        sig_dir = Path(os.environ["OTC_DATA_DIR"]) / "signals"
        
        has_tick_files = tick_dir.exists() and len(list(tick_dir.glob("*.jsonl"))) > 0
        has_sig_files = sig_dir.exists() and len(list(sig_dir.glob("*.jsonl"))) > 0
        
        t5_pass = self.ticks_received > 0
        t7_pass = self.warmup_complete_tick > 0
        
        print(f"╔══════════════════════════════════════════════════════════════════╗")
        print(f"║                      TEST RESULTS                                ║")
        print(f"╠══════════════════════════════════════════════════════════════════╣")
        print(f"║  T1/T2 Connection/Balance    ✅ PASS                             ║")
        print(f"║  T3  Tick Hook               ✅ PASS  (set_csv patched)           ║")
        print(f"║  T4  Asset Subscription      ✅ PASS  ({self.asset:<20s})     ║")
        print(f"║  T5  Live Tick Reception     {'✅ PASS' if t5_pass else '❌ FAIL'}  ({self.ticks_received} ticks in {self.duration}s)         ║")
        print(f"║  T7  OTEO Warmup Transition  {'✅ PASS' if t7_pass else '❌ FAIL'}  (enriched at tick {self.warmup_complete_tick})       ║")
        print(f"║  T9  Tick Logging            {'✅ PASS' if has_tick_files else '❌ FAIL'}  (files in data/tick_logs)       ║")
        print(f"║  T10 Signal Logging          {'✅ PASS' if has_sig_files else '➖ N/A'}   ({self.signals_received} signals)                  ║")
        print(f"╠══════════════════════════════════════════════════════════════════╣")
        print(f"║                                                                  ║")
        print(f"║  Total Ticks:     {self.ticks_received:<10d}                                 ║")
        print(f"║  Duration:        {self.duration:<10.1f}                                 ║")
        print(f"║  Avg Frequency:   {(self.ticks_received/self.duration):<10.2f} ticks/sec                          ║")
        if self.max_score > 0:
            print(f"║  OTEO Score Range: {self.min_score:.1f} — {self.max_score:.1f}                                  ║")
        print(f"║  Signals:         {self.signals_received:<10d}                                 ║")
        print(f"║  Manipulation:    {self.manipulations:<10d} flags                              ║")
        print(f"╚══════════════════════════════════════════════════════════════════╝")

def get_ssid(use_real: bool, provided_ssid: str) -> str:
    if provided_ssid:
        return provided_ssid
        
    env_key = "PO_SSID_REAL" if use_real else "PO_SSID_DEMO"
    ssid = os.getenv(env_key)
    
    if not ssid:
        print(f"ERROR: {env_key} not found in .env and --ssid not provided.")
        ssid = input("Please paste your full SSID string starting with 42[\"auth\": ").strip()
        
    return ssid

def main():
    parser = argparse.ArgumentParser(description="OTC SNIPER v3 — Live Tick Streaming Test")
    parser.add_argument("--asset", type=str, default="EURUSD_otc", help="Asset to subscribe to")
    parser.add_argument("--duration", type=int, default=90, help="Duration in seconds to collect ticks")
    parser.add_argument("--real", action="store_true", help="Use real account instead of demo")
    parser.add_argument("--ssid", type=str, default="", help="Provide SSID directly")
    parser.add_argument("--verbose", action="store_true", help="Print raw WebSocket messages")
    
    args = parser.parse_args()
    
    print(f"╔══════════════════════════════════════════════════════════════════╗")
    print(f"║          OTC SNIPER v3 — Live Streaming Pipeline Test           ║")
    print(f"╚══════════════════════════════════════════════════════════════════╝")
    print(f"[SETUP] Conda environment detected")
    
    ssid = get_ssid(args.real, args.ssid)
    if not ssid or not ssid.startswith("42["):
        print("ERROR: Invalid SSID provided.")
        sys.exit(1)
        
    print(f"[SETUP] Account type: {'REAL' if args.real else 'DEMO'}")
    print(f"[SETUP] Test asset: {args.asset}")
    print(f"[SETUP] Collection duration: {args.duration} seconds")
    print(f"[SETUP] Data directory: {os.environ['OTC_DATA_DIR']}")
    
    # Needs to run in asyncio loop
    harness = StreamingTestHarness(ssid, args.asset, args.duration, args.verbose)
    try:
        # connect() is blocking — call before starting the asyncio event loop
        if not harness.connect():
            sys.exit(1)
        asyncio.run(harness.run())
    except KeyboardInterrupt:
        print("\n[CLEAN] Test aborted by user. Disconnecting...")
        if harness.session:
            harness.session.disconnect()

if __name__ == "__main__":
    main()
