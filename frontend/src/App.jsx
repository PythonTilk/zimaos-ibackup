import { useState, useEffect } from 'react'

const API_BASE = '/api'; // Using relative paths for Docker setup

function App() {
  const [devices, setDevices] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDevices = async () => {
    try {
      const res = await fetch(`${API_BASE}/devices`);
      const data = await res.json();
      setDevices(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/logs`);
      const data = await res.json();
      setLogs(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchDevices();
    fetchLogs();
    const interval = setInterval(() => {
      fetchDevices();
      fetchLogs();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handlePair = async (udid) => {
    try {
      const res = await fetch(`${API_BASE}/devices/${udid}/pair`, { method: 'POST' });
      const data = await res.json();
      alert(data.message || data.detail);
      fetchDevices();
    } catch (e) {
      alert("Error pairing");
    }
  };

  const handleBackup = async (udid) => {
    try {
      const res = await fetch(`${API_BASE}/devices/${udid}/backup`, { method: 'POST' });
      const data = await res.json();
      alert(data.message || data.detail);
    } catch (e) {
      alert("Error starting backup");
    }
  };

  const saveConfig = async (udid, path, strategy) => {
    try {
      await fetch(`${API_BASE}/devices/${udid}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backup_path: path, overwrite_strategy: strategy })
      });
      alert("Settings saved!");
      fetchDevices();
    } catch (e) {
      alert("Error saving settings");
    }
  };

  if (loading) return <div className="p-10 text-center">Loading devices...</div>;

  return (
    <div className="container mx-auto p-4 max-w-5xl">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">iBackup for ZimaOS</h1>
        <p className="text-gray-500">Auto Wi-Fi Backups via libimobiledevice</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-xl font-semibold mb-4 border-b pb-2">Devices</h2>
          {devices.length === 0 ? (
            <p className="text-gray-500">No devices found. Connect an iPhone via USB first.</p>
          ) : (
            devices.map(dev => (
              <DeviceCard 
                key={dev.udid} 
                device={dev} 
                onPair={() => handlePair(dev.udid)}
                onBackup={() => handleBackup(dev.udid)}
                onSaveConfig={saveConfig}
              />
            ))
          )}
        </div>

        <div>
          <h2 className="text-xl font-semibold mb-4 border-b pb-2">Recent Logs</h2>
          <div className="bg-gray-900 text-green-400 p-4 rounded h-96 overflow-y-auto font-mono text-sm">
            {logs.length === 0 && <p className="text-gray-500">No logs yet.</p>}
            {logs.map(log => (
              <div key={log.id} className="mb-1">
                <span className="text-gray-500">[{log.timestamp}]</span>{' '}
                <span className={log.level === 'ERROR' ? 'text-red-400' : 'text-blue-300'}>[{log.level}]</span>{' '}
                {log.message}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function DeviceCard({ device, onPair, onBackup, onSaveConfig }) {
  const [path, setPath] = useState(device.backup_path || `/backups/${device.udid}`);
  const [strategy, setStrategy] = useState(device.overwrite_strategy || 'incremental');

  return (
    <div className="bg-white p-5 rounded shadow mb-4">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-bold">{device.name}</h3>
          <p className="text-xs text-gray-500">UDID: {device.udid.substring(0,8)}...</p>
        </div>
        <div>
          {device.connected ? (
            <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
              Connected ({device.connection_type})
            </span>
          ) : (
            <span className="bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded-full">
              Offline
            </span>
          )}
        </div>
      </div>

      <div className="mb-4 text-sm">
        <p><strong>Status:</strong> {device.paired ? 'Paired (Trusted)' : 'Not Paired'}</p>
        <p><strong>Last Backup:</strong> {device.last_backup_time || 'Never'}</p>
      </div>

      <div className="bg-gray-50 p-3 rounded mb-4 text-sm">
        <label className="block mb-2 font-medium text-gray-700">Backup Path (in Container)</label>
        <input 
          type="text" 
          value={path}
          onChange={e => setPath(e.target.value)}
          className="w-full border p-2 rounded mb-3"
        />

        <label className="block mb-2 font-medium text-gray-700">Backup Strategy</label>
        <select 
          value={strategy}
          onChange={e => setStrategy(e.target.value)}
          className="w-full border p-2 rounded mb-3"
        >
          <option value="incremental">Incremental (Update existing - Recommended)</option>
          <option value="full">Full Overwrite (Delete old & backup fresh)</option>
        </select>

        <button 
          onClick={() => onSaveConfig(device.udid, path, strategy)}
          className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm w-full"
        >
          Save Settings
        </button>
      </div>

      <div className="flex gap-2">
        {!device.paired && device.connected && (
          <button 
            onClick={onPair}
            className="flex-1 bg-yellow-500 hover:bg-yellow-600 text-white py-2 rounded font-medium"
          >
            Pair (Trust on device)
          </button>
        )}
        {device.paired && device.connected && (
          <button 
            onClick={onBackup}
            className="flex-1 bg-green-500 hover:bg-green-600 text-white py-2 rounded font-medium"
          >
            Backup Now
          </button>
        )}
      </div>
    </div>
  );
}

export default App;
