import React, { useState } from 'react';
import { User, ChevronDown, Settings, LogOut, Wifi, WifiOff, Activity, Chrome, Radio } from 'lucide-react';

/**
 * TopBar Component
 * 
 * Provides a native menubar/topbar with:
 * - Connection status indicators (WS, Chrome, Stream, SSID)
 * - Profile menu placeholder (expandable for future development)
 * 
 * Status colors:
 * - connected/streaming: accent-green with glow
 * - error: accent-red with glow
 * - default/connecting: amber/warning
 */
import { useAuth } from '../context/AuthContext';

const TopBar = ({ 
  streamStatus = 'disconnected',
  chromeStatus = 'disconnected', 
  ssidStatus = 'disconnected',
  onLogout,
  onStartChrome,
  onStopChrome,
  onStartStream,
  onStopStream,
  onStartSsid,
  onStopSsid,
  isBusy = { chrome: false, stream: false, ssid: false }
}) => {
  const [profileOpen, setProfileOpen] = useState(false);
  const { user } = useAuth();

  // Determine if buttons should show start or stop
  const isChromeActive = chromeStatus === 'connected';
  const isStreamActive = streamStatus === 'streaming' || streamStatus === 'connected';
  const isSsidActive = ssidStatus === 'connected';

  return (
    <header className="h-14 glass-card border-b border-white/5 flex items-center justify-between px-6 z-20 flex-none">
      {/* ── LEFT: Status Badges ─────────────────────────────── */}
      <div className="flex items-center gap-3">
        
        {/* WebSocket Status */}
        <StatusBadge 
          label="WS" 
          status={streamStatus === 'disconnected' ? 'default' : 'connected'}
          icon={<Wifi className="w-3 h-3" />}
        />

        {/* Chrome Status */}
        <StatusBadge 
          label="Chrome" 
          status={chromeStatus}
          isActive={isChromeActive}
          onClick={isChromeActive ? onStopChrome : onStartChrome}
          disabled={isBusy.chrome}
          busyLabel={isChromeActive ? 'Stopping...' : 'Starting...'}
          icon={<Chrome className="w-3 h-3" />}
        />

        {/* Stream Status */}
        <StatusBadge 
          label="Stream" 
          status={streamStatus}
          isActive={isStreamActive}
          onClick={isStreamActive ? onStopStream : onStartStream}
          disabled={isBusy.stream}
          busyLabel={isStreamActive ? 'Pausing...' : 'Starting...'}
          icon={<Radio className="w-3 h-3" />}
        />

        {/* SSID Status */}
        <StatusBadge 
          label="SSID" 
          status={ssidStatus}
          isActive={isSsidActive}
          onClick={isSsidActive ? onStopSsid : onStartSsid}
          disabled={isBusy.ssid}
          busyLabel={isSsidActive ? 'Stopping...' : 'Starting...'}
          icon={<Activity className="w-3 h-3" />}
        />
        
        {/* Broker Selector */}
        <div className="flex items-center ml-2 border-l border-white/10 pl-4">
          <select 
            className="bg-transparent text-xs text-slate-300 font-bold focus:outline-none cursor-pointer"
            defaultValue="pocket_option"
          >
            <option value="pocket_option" className="bg-slate-800 text-white">Pocket Option</option>
            <option value="deriv" className="bg-slate-800 text-white" disabled>Deriv (Coming Soon)</option>
            <option value="binance" className="bg-slate-800 text-white" disabled>Binance (Coming Soon)</option>
          </select>
        </div>
      </div>

      {/* ── RIGHT: Profile Menu ──────────────────────────────── */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setProfileOpen(!profileOpen)}
          className="flex items-center gap-2 px-3 py-1.5 glass-card rounded-lg border border-white/10
                     hover:border-cyan/30 hover:shadow-glow-cyan transition-all"
        >
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-cyan/40 to-neon/40 
                          flex items-center justify-center border border-white/20">
            <User className="w-4 h-4 text-white" />
          </div>
          <span className="text-xs font-bold text-slate-300">Profile</span>
          <ChevronDown className={`w-3 h-3 text-slate-500 transition-transform ${profileOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Profile Dropdown */}
        {profileOpen && (
          <>
            {/* Backdrop */}
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setProfileOpen(false)} 
            />
            
            {/* Menu */}
            <div className="absolute right-0 mt-2 w-56 glass-card rounded-xl border border-white/10 
                           shadow-xl z-50 overflow-hidden">
              {/* Header */}
              <div className="px-4 py-3 border-b border-white/5">
                <p className="text-xs font-bold text-white">{user?.username || 'Guest User'}</p>
                <p className="text-[10px] text-slate-500 mt-0.5 capitalize">{user?.role || 'Viewer'}</p>
              </div>
              
              {/* Menu Items */}
              <div className="py-1">
                <ProfileMenuItem 
                  icon={<User className="w-4 h-4" />}
                  label="Account"
                  description="Manage users & keys"
                  onClick={() => {
                    setProfileOpen(false);
                    // The actual navigation should be managed by the parent, but for now we rely on the sidebar
                  }}
                />
                <ProfileMenuItem 
                  icon={<LogOut className="w-4 h-4 text-red-400" />}
                  label="Logout"
                  onClick={() => {
                    setProfileOpen(false);
                    if(onLogout) onLogout();
                  }}
                />
              </div>
              
              {/* Footer */}
              <div className="px-4 py-2 border-t border-white/5 bg-white/[0.02]">
                <p className="text-[9px] text-slate-600 text-center">
                  v0.1.0 — Profile feature pending
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </header>
  );
};

/**
 * StatusBadge Component
 * 
 * Individual status indicator button with:
 * - Label text
 * - Status color indicator (dot)
 * - Optional click handler
 * - Busy/loading state
 */
const StatusBadge = ({ 
  label, 
  status, 
  isActive = false,
  onClick, 
  disabled = false, 
  busyLabel,
  icon
}) => {
  const getStatusColor = (s) => {
    switch(s) {
      case 'connected':
      case 'streaming':
        return 'bg-neon shadow-[0_0_8px_rgba(0,255,157,0.6)]';
      case 'error':
        return 'bg-signal shadow-[0_0_8px_rgba(255,59,92,0.6)]';
      case 'connecting':
      case 'pending':
        return 'bg-amber shadow-[0_0_8px_rgba(255,149,0,0.6)] animate-pulse';
      default:
        return 'bg-slate-500 shadow-[0_0_4px_rgba(100,116,139,0.4)]';
    }
  };

  const labelText = disabled && busyLabel ? busyLabel : label;

  const buttonClass = `
    flex items-center gap-2 px-3 py-1.5 glass-card rounded-lg border border-white/10
    transition-all group
    ${onClick ? 'hover:border-white/20 hover:bg-white/[0.05] cursor-pointer' : ''}
    ${disabled ? 'opacity-60 cursor-not-allowed' : ''}
    ${isActive ? 'border-neon/30 bg-neon/5' : ''}
  `;

  if (onClick) {
    return (
      <button 
        type="button" 
        className={buttonClass} 
        onClick={onClick} 
        disabled={disabled}
      >
        {icon && (
          <span className={`${disabled ? 'text-slate-500' : 'text-slate-400 group-hover:text-white'} transition-colors`}>
            {icon}
          </span>
        )}
        <span className="text-[10px] font-bold text-slate-400 group-hover:text-white uppercase tracking-wider transition-colors">
          {labelText}
        </span>
        <div className={`w-2 h-2 rounded-full ${getStatusColor(status)}`} />
      </button>
    );
  }

  return (
    <div className={buttonClass}>
      {icon && (
        <span className="text-slate-400">{icon}</span>
      )}
      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
        {labelText}
      </span>
      <div className={`w-2 h-2 rounded-full ${getStatusColor(status)}`} />
    </div>
  );
};

/**
 * ProfileMenuItem Component
 * 
 * Individual item in the profile dropdown menu.
 * Shows disabled state for placeholder items.
 */
const ProfileMenuItem = ({ icon, label, description, disabled = false, onClick }) => {
  const itemClass = `
    flex items-center gap-3 px-4 py-2.5 transition-all
    ${disabled 
      ? 'opacity-50 cursor-not-allowed' 
      : 'hover:bg-white/[0.05] cursor-pointer'
    }
  `;

  return (
    <div className={itemClass} onClick={disabled ? undefined : onClick}>
      <span className="text-slate-500">{icon}</span>
      <div className="flex flex-col">
        <span className={`text-xs font-bold ${disabled ? 'text-slate-600' : 'text-white'}`}>
          {label}
        </span>
        {description && (
          <span className="text-[9px] text-slate-600">{description}</span>
        )}
      </div>
    </div>
  );
};

export default TopBar;
