import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { 
  User, 
  MessageCircle, 
  Mic, 
  Video, 
  Settings, 
  Plus, 
  Play, 
  Pause, 
  Square,
  Upload,
  Brain,
  Users
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Components
const CreateProfileModal = ({ isOpen, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: '',
    role: '',
    personality: '',
    response_style: '',
    meeting_topics: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const profileData = {
      ...formData,
      meeting_topics: formData.meeting_topics.split(',').map(t => t.trim()).filter(t => t)
    };
    onSave(profileData);
    setFormData({ name: '', role: '', personality: '', response_style: '', meeting_topics: '' });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h2 className="text-xl font-bold mb-4">Create Meeting Profile</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Profile Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full p-3 border border-gray-300 rounded-lg"
            required
          />
          <input
            type="text"
            placeholder="Role (e.g., Product Manager, Developer)"
            value={formData.role}
            onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            className="w-full p-3 border border-gray-300 rounded-lg"
            required
          />
          <textarea
            placeholder="Personality (e.g., Professional, friendly, analytical)"
            value={formData.personality}
            onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
            className="w-full p-3 border border-gray-300 rounded-lg h-20"
            required
          />
          <textarea
            placeholder="Response Style (e.g., Brief and to the point, Detailed explanations)"
            value={formData.response_style}
            onChange={(e) => setFormData({ ...formData, response_style: e.target.value })}
            className="w-full p-3 border border-gray-300 rounded-lg h-20"
            required
          />
          <input
            type="text"
            placeholder="Meeting Topics (comma-separated)"
            value={formData.meeting_topics}
            onChange={(e) => setFormData({ ...formData, meeting_topics: e.target.value })}
            className="w-full p-3 border border-gray-300 rounded-lg"
          />
          <div className="flex gap-3 mt-6">
            <button
              type="submit"
              className="flex-1 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create Profile
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-400 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const VoiceUploadModal = ({ isOpen, onClose, onUpload }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [voiceName, setVoiceName] = useState('');
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && (file.type.includes('audio') || file.type.includes('video'))) {
      setSelectedFile(file);
    } else {
      alert('Please select an audio or video file');
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile || !voiceName.trim()) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('audio_file', selectedFile);
      formData.append('name', voiceName.trim());

      await onUpload(formData);
      setSelectedFile(null);
      setVoiceName('');
      onClose();
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <h2 className="text-xl font-bold mb-4">Upload Voice Sample</h2>
        <form onSubmit={handleUpload} className="space-y-4">
          <input
            type="text"
            placeholder="Voice Profile Name"
            value={voiceName}
            onChange={(e) => setVoiceName(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-lg"
            required
          />
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <input
              type="file"
              accept="audio/*,video/*"
              onChange={handleFileChange}
              className="hidden"
              id="voice-file"
            />
            <label htmlFor="voice-file" className="cursor-pointer">
              <Upload className="mx-auto mb-2" size={32} />
              {selectedFile ? selectedFile.name : 'Click to select audio file'}
            </label>
          </div>
          <p className="text-sm text-gray-600">
            Upload 20+ seconds of clear speech for best voice cloning results
          </p>
          <div className="flex gap-3 mt-6">
            <button
              type="submit"
              disabled={!selectedFile || !voiceName.trim() || uploading}
              className="flex-1 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
            >
              {uploading ? 'Uploading...' : 'Upload Voice'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-400 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const MeetingSimulator = ({ session, profile, onClose }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [ws, setWs] = useState(null);
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    // Connect to WebSocket
    const wsUrl = `wss://d1420574-b155-4b5e-8574-b7eb736318b6.preview.emergentagent.com/api/sessions/${session.id}/live`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      setIsConnected(true);
      setWs(websocket);
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'ai_response') {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.content,
          speaker: data.speaker,
          timestamp: new Date().toLocaleTimeString()
        }]);
        
        // Use browser's speech synthesis
        if ('speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(data.content);
          utterance.rate = 0.9;
          utterance.pitch = 1.0;
          speechSynthesis.speak(utterance);
        }
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      websocket.close();
    };
  }, [session.id]);

  const sendMessage = (content, speaker = "Meeting Participant") => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'message',
        content,
        speaker
      }));
      
      setMessages(prev => [...prev, {
        role: 'user',
        content,
        speaker,
        timestamp: new Date().toLocaleTimeString()
      }]);
    }
  };

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (inputMessage.trim()) {
      sendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  const simulateMeetingScenarios = () => {
    const scenarios = [
      { speaker: "Manager", message: "Can you give us a quick status update on your current project?" },
      { speaker: "Client", message: "What's your timeline for delivery?" },
      { speaker: "Team Lead", message: "Do you have any blockers we should know about?" },
      { speaker: "Stakeholder", message: "How does this align with our quarterly goals?" },
      { speaker: "Colleague", message: "Would you like to share your screen and walk us through this?" }
    ];
    
    const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
    sendMessage(scenario.message, scenario.speaker);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-4xl mx-4 h-5/6 flex flex-col">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="font-bold">Live Meeting - {session.title}</span>
            </div>
            <div className="text-sm text-gray-600">
              Acting as: {profile.name} ({profile.role})
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={simulateMeetingScenarios}
              className="px-3 py-1 bg-blue-100 text-blue-600 rounded text-sm hover:bg-blue-200"
            >
              Simulate Question
            </button>
            <button
              onClick={onClose}
              className="px-3 py-1 bg-red-100 text-red-600 rounded text-sm hover:bg-red-200"
            >
              End Meeting
            </button>
          </div>
        </div>
        
        <div className="flex-1 p-4 overflow-y-auto bg-gray-50">
          <div className="space-y-3">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'assistant' ? 'justify-start' : 'justify-end'}`}>
                <div className={`max-w-xs lg:max-w-md px-3 py-2 rounded-lg ${
                  msg.role === 'assistant' 
                    ? 'bg-blue-100 text-blue-900' 
                    : 'bg-white border border-gray-200'
                }`}>
                  <div className="text-xs text-gray-500 mb-1">
                    {msg.speaker} • {msg.timestamp}
                  </div>
                  <div>{msg.content}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="p-4 border-t border-gray-200">
          <form onSubmit={handleSendMessage} className="flex gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Simulate someone speaking in the meeting..."
              className="flex-1 p-3 border border-gray-300 rounded-lg"
            />
            <button
              type="submit"
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <MessageCircle size={18} />
              Send
            </button>
          </form>
          <div className="text-xs text-gray-500 mt-2">
            💡 The AI will automatically respond to messages and speak using text-to-speech
          </div>
        </div>
      </div>
    </div>
  );
};

function App() {
  const [activeTab, setActiveTab] = useState('profiles');
  const [profiles, setProfiles] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [voiceProfiles, setVoiceProfiles] = useState([]);
  const [showCreateProfile, setShowCreateProfile] = useState(false);
  const [showVoiceUpload, setShowVoiceUpload] = useState(false);
  const [activeMeeting, setActiveMeeting] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [profilesRes, sessionsRes, voiceRes] = await Promise.all([
        axios.get(`${API}/profiles`),
        axios.get(`${API}/sessions`),
        axios.get(`${API}/voice/profiles`)
      ]);
      setProfiles(profilesRes.data);
      setSessions(sessionsRes.data);
      setVoiceProfiles(voiceRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const createProfile = async (profileData) => {
    try {
      setLoading(true);
      await axios.post(`${API}/profiles`, profileData);
      setShowCreateProfile(false);
      await loadData();
    } catch (error) {
      console.error('Failed to create profile:', error);
      alert('Failed to create profile');
    } finally {
      setLoading(false);
    }
  };

  const startMeeting = async (profile) => {
    try {
      setLoading(true);
      const sessionData = {
        title: `Meeting with ${profile.name}`,
        profile_id: profile.id,
        participants: ["Meeting Participants"]
      };
      
      const response = await axios.post(`${API}/sessions`, sessionData);
      const session = response.data;
      
      setActiveMeeting({ session, profile });
      await loadData();
    } catch (error) {
      console.error('Failed to start meeting:', error);
      alert('Failed to start meeting');
    } finally {
      setLoading(false);
    }
  };

  const uploadVoice = async (formData) => {
    try {
      await axios.post(`${API}/voice/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      await loadData();
    } catch (error) {
      console.error('Failed to upload voice:', error);
      throw error;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🤖 AI Meeting Assistant
          </h1>
          <p className="text-gray-600">
            Your intelligent AI avatar for automated meeting attendance
          </p>
        </div>

        {/* Navigation */}
        <div className="flex justify-center mb-8">
          <div className="bg-white rounded-lg p-1 shadow-sm">
            {[
              { key: 'profiles', label: 'Profiles', icon: User },
              { key: 'sessions', label: 'Sessions', icon: Users },
              { key: 'voice', label: 'Voice Setup', icon: Mic }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`px-4 py-2 rounded-md flex items-center gap-2 transition-colors ${
                  activeTab === key
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="max-w-6xl mx-auto">
          {activeTab === 'profiles' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900">Meeting Profiles</h2>
                <button
                  onClick={() => setShowCreateProfile(true)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
                >
                  <Plus size={18} />
                  Create Profile
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {profiles.map((profile) => (
                  <div key={profile.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="font-bold text-lg text-gray-900">{profile.name}</h3>
                        <p className="text-sm text-gray-600">{profile.role}</p>
                      </div>
                      <Brain className="text-blue-600" size={24} />
                    </div>
                    
                    <div className="space-y-2 mb-4">
                      <p className="text-sm"><strong>Personality:</strong> {profile.personality}</p>
                      <p className="text-sm"><strong>Response Style:</strong> {profile.response_style}</p>
                      {profile.meeting_topics.length > 0 && (
                        <div className="text-sm">
                          <strong>Topics:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {profile.meeting_topics.map((topic, idx) => (
                              <span key={idx} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                                {topic}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => startMeeting(profile)}
                      disabled={loading}
                      className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 disabled:bg-gray-400 flex items-center justify-center gap-2"
                    >
                      <Video size={18} />
                      Start AI Meeting
                    </button>
                  </div>
                ))}
              </div>

              {profiles.length === 0 && (
                <div className="text-center py-12">
                  <Brain size={64} className="mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-semibold text-gray-600 mb-2">No profiles yet</h3>
                  <p className="text-gray-500 mb-4">Create your first AI meeting profile to get started</p>
                  <button
                    onClick={() => setShowCreateProfile(true)}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
                  >
                    Create Your First Profile
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'sessions' && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900">Meeting Sessions</h2>
              
              <div className="space-y-4">
                {sessions.map((session) => (
                  <div key={session.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-bold text-lg text-gray-900">{session.title}</h3>
                        <p className="text-sm text-gray-600">
                          Created: {new Date(session.created_at).toLocaleString()}
                        </p>
                        <p className="text-sm text-gray-600">
                          Status: <span className={`px-2 py-1 rounded text-xs ${
                            session.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {session.status}
                          </span>
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600">
                          {session.conversation_history?.length || 0} messages
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {sessions.length === 0 && (
                <div className="text-center py-12">
                  <Users size={64} className="mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-semibold text-gray-600 mb-2">No sessions yet</h3>
                  <p className="text-gray-500">Start your first meeting to see sessions here</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'voice' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-900">Voice Setup</h2>
                <button
                  onClick={() => setShowVoiceUpload(true)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
                >
                  <Upload size={18} />
                  Upload Voice Sample
                </button>
              </div>

              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="text-center mb-6">
                  <Mic size={64} className="mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-semibold text-gray-600 mb-2">Voice Cloning Setup</h3>
                  <p className="text-gray-500">
                    Upload voice samples to enable realistic voice synthesis for meetings
                  </p>
                </div>

                {voiceProfiles.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-semibold text-gray-900">Uploaded Voice Profiles:</h4>
                    {voiceProfiles.map((voice) => (
                      <div key={voice.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <span className="font-medium">{voice.name}</span>
                          <span className="text-sm text-gray-600 ml-2">
                            ({voice.duration}s)
                          </span>
                        </div>
                        <span className="text-green-600 text-sm">✓ Ready</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-2">Current Status:</h4>
                  <p className="text-blue-800 text-sm">
                    🔊 Using browser text-to-speech for now. 
                    Add ElevenLabs API key to backend for advanced voice cloning.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modals */}
        <CreateProfileModal
          isOpen={showCreateProfile}
          onClose={() => setShowCreateProfile(false)}
          onSave={createProfile}
        />

        <VoiceUploadModal
          isOpen={showVoiceUpload}
          onClose={() => setShowVoiceUpload(false)}
          onUpload={uploadVoice}
        />

        {activeMeeting && (
          <MeetingSimulator
            session={activeMeeting.session}
            profile={activeMeeting.profile}
            onClose={() => setActiveMeeting(null)}
          />
        )}
      </div>
    </div>
  );
}

export default App;