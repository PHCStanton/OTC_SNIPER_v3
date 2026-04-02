import { useState, useEffect } from 'react';
import { Bot, RefreshCw } from 'lucide-react';
import { getAIStatus } from '../../api/aiApi.js';
import AITab from './AITab.jsx';

export default function AiSessionPanel() {
  const [aiStatus, setAIStatus] = useState({ enabled: false, provider: 'xai', model: '', has_api_key: false, reason: '' });
  const [statusLoading, setStatusLoading] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function loadAIStatus() {
      setStatusLoading(true);
      try {
        const status = await getAIStatus();
        if (mounted) setAIStatus(status);
      } catch (error) {
        if (mounted) {
          setAIStatus({ enabled: false, provider: 'xai', model: '', has_api_key: false, reason: error.message });
        }
      } finally {
        if (mounted) setStatusLoading(false);
      }
    }

    loadAIStatus();

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="flex flex-col h-full bg-[#0f1419] p-4 rounded-2xl border border-white/5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
            <Bot size={20} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-[#e3e6e7]">AI Assistant</h2>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">Trading Intelligence</p>
          </div>
        </div>
        
        <button
          onClick={async () => {
            setStatusLoading(true);
            try {
              const status = await getAIStatus();
              setAIStatus(status);
            } finally {
              setStatusLoading(false);
            }
          }}
          className="p-2 rounded-lg text-gray-500 hover:bg-white/5 hover:text-white transition-colors"
          title="Refresh AI Status"
        >
          <RefreshCw size={14} className={statusLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <AITab
          aiStatus={aiStatus}
          statusLoading={statusLoading}
          onStatusRefresh={async () => {
            try {
              setStatusLoading(true);
              const status = await getAIStatus();
              setAIStatus(status);
            } finally {
              setStatusLoading(false);
            }
          }}
        />
      </div>
    </div>
  );
}