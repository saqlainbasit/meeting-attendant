#!/usr/bin/env python3
"""
AI Meeting Assistant Backend API Tests
Tests all backend functionality including API connectivity, CRUD operations, 
Gemini AI integration, WebSocket functionality, and voice upload.
"""

import requests
import json
import asyncio
import websockets
import base64
import io
import time
from datetime import datetime
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://d1420574-b155-4b5e-8574-b7eb736318b6.preview.emergentagent.com/api"
WEBSOCKET_URL = "wss://d1420574-b155-4b5e-8574-b7eb736318b6.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = {}
        self.created_profiles = []
        self.created_sessions = []
        self.created_voice_profiles = []

    def log_result(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test result"""
        self.test_results[test_name] = {
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")

    def test_basic_api_connectivity(self):
        """Test 1: Basic API Setup - GET /api/"""
        try:
            response = self.session.get(f"{BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "AI Meeting Assistant API" in data["message"]:
                    self.log_result("Basic API Connectivity", True, "API root endpoint working correctly")
                    return True
                else:
                    self.log_result("Basic API Connectivity", False, "Unexpected response format", data)
                    return False
            else:
                self.log_result("Basic API Connectivity", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Basic API Connectivity", False, f"Connection error: {str(e)}")
            return False

    def test_meeting_profile_crud(self):
        """Test 2: Meeting Profile Management - CRUD operations"""
        try:
            # Test CREATE profile
            profile_data = {
                "name": "Sarah Johnson",
                "role": "Senior Product Manager",
                "personality": "Professional, analytical, and collaborative",
                "response_style": "Concise and data-driven",
                "meeting_topics": ["Product Strategy", "User Experience", "Market Analysis"]
            }
            
            create_response = self.session.post(f"{BASE_URL}/profiles", json=profile_data)
            if create_response.status_code != 200:
                self.log_result("Profile CRUD - Create", False, f"Create failed: HTTP {create_response.status_code}", create_response.text)
                return False
            
            created_profile = create_response.json()
            profile_id = created_profile["id"]
            self.created_profiles.append(profile_id)
            
            # Verify profile structure
            required_fields = ["id", "name", "role", "personality", "response_style", "meeting_topics", "created_at"]
            missing_fields = [field for field in required_fields if field not in created_profile]
            if missing_fields:
                self.log_result("Profile CRUD - Create", False, f"Missing fields: {missing_fields}")
                return False
            
            # Test READ - Get all profiles
            list_response = self.session.get(f"{BASE_URL}/profiles")
            if list_response.status_code != 200:
                self.log_result("Profile CRUD - List", False, f"List failed: HTTP {list_response.status_code}")
                return False
            
            profiles = list_response.json()
            if not isinstance(profiles, list):
                self.log_result("Profile CRUD - List", False, "Response is not a list")
                return False
            
            # Test READ - Get specific profile
            get_response = self.session.get(f"{BASE_URL}/profiles/{profile_id}")
            if get_response.status_code != 200:
                self.log_result("Profile CRUD - Get", False, f"Get failed: HTTP {get_response.status_code}")
                return False
            
            retrieved_profile = get_response.json()
            if retrieved_profile["id"] != profile_id:
                self.log_result("Profile CRUD - Get", False, "Retrieved profile ID mismatch")
                return False
            
            self.log_result("Meeting Profile CRUD", True, f"All CRUD operations successful. Created profile: {profile_id}")
            return True
            
        except Exception as e:
            self.log_result("Meeting Profile CRUD", False, f"Exception: {str(e)}")
            return False

    def test_gemini_ai_integration(self):
        """Test 3: Gemini AI Integration - Chat functionality"""
        try:
            # First create a session (need profile and session for chat)
            if not self.created_profiles:
                self.log_result("Gemini AI Integration", False, "No profiles available for testing")
                return False
            
            profile_id = self.created_profiles[0]
            
            # Create a session
            session_data = {
                "title": "AI Integration Test Meeting",
                "profile_id": profile_id,
                "participants": ["John Doe", "Jane Smith"]
            }
            
            session_response = self.session.post(f"{BASE_URL}/sessions", json=session_data)
            if session_response.status_code != 200:
                self.log_result("Gemini AI Integration", False, f"Session creation failed: HTTP {session_response.status_code}")
                return False
            
            session = session_response.json()
            session_id = session["id"]
            self.created_sessions.append(session_id)
            
            # Test chat functionality
            test_message = "Hello, can you introduce yourself and tell us about your role in this meeting?"
            
            # Note: The chat endpoint expects form data, not JSON
            chat_response = self.session.post(
                f"{BASE_URL}/sessions/{session_id}/chat",
                params={"message": test_message}
            )
            
            if chat_response.status_code != 200:
                self.log_result("Gemini AI Integration", False, f"Chat failed: HTTP {chat_response.status_code}", chat_response.text)
                return False
            
            ai_response = chat_response.json()
            
            # Verify response structure
            required_fields = ["message", "confidence", "response_type"]
            missing_fields = [field for field in required_fields if field not in ai_response]
            if missing_fields:
                self.log_result("Gemini AI Integration", False, f"Missing response fields: {missing_fields}")
                return False
            
            # Verify response content
            if not ai_response["message"] or len(ai_response["message"]) < 10:
                self.log_result("Gemini AI Integration", False, "AI response too short or empty")
                return False
            
            self.log_result("Gemini AI Integration", True, f"AI responded successfully: '{ai_response['message'][:100]}...'")
            return True
            
        except Exception as e:
            self.log_result("Gemini AI Integration", False, f"Exception: {str(e)}")
            return False

    def test_meeting_session_management(self):
        """Test 4: Meeting Session Management - CRUD operations"""
        try:
            if not self.created_profiles:
                self.log_result("Session Management", False, "No profiles available for testing")
                return False
            
            profile_id = self.created_profiles[0]
            
            # Test CREATE session
            session_data = {
                "title": "Weekly Product Review",
                "profile_id": profile_id,
                "participants": ["Alice Cooper", "Bob Wilson", "Carol Davis"]
            }
            
            create_response = self.session.post(f"{BASE_URL}/sessions", json=session_data)
            if create_response.status_code != 200:
                self.log_result("Session Management - Create", False, f"Create failed: HTTP {create_response.status_code}")
                return False
            
            created_session = create_response.json()
            session_id = created_session["id"]
            self.created_sessions.append(session_id)
            
            # Verify session structure
            required_fields = ["id", "title", "profile_id", "participants", "status", "created_at"]
            missing_fields = [field for field in required_fields if field not in created_session]
            if missing_fields:
                self.log_result("Session Management - Create", False, f"Missing fields: {missing_fields}")
                return False
            
            # Test READ - Get all sessions
            list_response = self.session.get(f"{BASE_URL}/sessions")
            if list_response.status_code != 200:
                self.log_result("Session Management - List", False, f"List failed: HTTP {list_response.status_code}")
                return False
            
            sessions = list_response.json()
            if not isinstance(sessions, list):
                self.log_result("Session Management - List", False, "Response is not a list")
                return False
            
            # Test READ - Get specific session
            get_response = self.session.get(f"{BASE_URL}/sessions/{session_id}")
            if get_response.status_code != 200:
                self.log_result("Session Management - Get", False, f"Get failed: HTTP {get_response.status_code}")
                return False
            
            # Test UPDATE - Update session status
            status_response = self.session.put(f"{BASE_URL}/sessions/{session_id}/status", params={"status": "paused"})
            if status_response.status_code != 200:
                self.log_result("Session Management - Update", False, f"Status update failed: HTTP {status_response.status_code}")
                return False
            
            self.log_result("Meeting Session Management", True, f"All session operations successful. Created session: {session_id}")
            return True
            
        except Exception as e:
            self.log_result("Meeting Session Management", False, f"Exception: {str(e)}")
            return False

    async def test_websocket_live_meeting(self):
        """Test 5: WebSocket Live Meeting - Real-time communication"""
        try:
            if not self.created_sessions:
                self.log_result("WebSocket Live Meeting", False, "No sessions available for testing")
                return False
            
            session_id = self.created_sessions[0]
            websocket_uri = f"{WEBSOCKET_URL}/sessions/{session_id}/live"
            
            async with websockets.connect(websocket_uri) as websocket:
                # Test connection
                try:
                    # Wait for connection message
                    connection_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    connection_data = json.loads(connection_msg)
                    
                    if connection_data.get("type") != "connected":
                        self.log_result("WebSocket Live Meeting", False, f"Unexpected connection message: {connection_data}")
                        return False
                    
                    # Test ping-pong
                    await websocket.send(json.dumps({"type": "ping"}))
                    pong_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    pong_data = json.loads(pong_msg)
                    
                    if pong_data.get("type") != "pong":
                        self.log_result("WebSocket Live Meeting", False, f"Ping-pong failed: {pong_data}")
                        return False
                    
                    # Test message exchange
                    test_message = {
                        "type": "message",
                        "content": "What are your thoughts on the current project timeline?",
                        "speaker": "Meeting Host"
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    response_msg = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    response_data = json.loads(response_msg)
                    
                    if response_data.get("type") != "ai_response":
                        self.log_result("WebSocket Live Meeting", False, f"Unexpected response type: {response_data}")
                        return False
                    
                    if not response_data.get("content") or len(response_data["content"]) < 10:
                        self.log_result("WebSocket Live Meeting", False, "AI response too short or empty")
                        return False
                    
                    self.log_result("WebSocket Live Meeting", True, f"WebSocket communication successful. AI responded: '{response_data['content'][:100]}...'")
                    return True
                    
                except asyncio.TimeoutError:
                    self.log_result("WebSocket Live Meeting", False, "WebSocket communication timeout")
                    return False
                    
        except Exception as e:
            self.log_result("WebSocket Live Meeting", False, f"Exception: {str(e)}")
            return False

    def test_voice_profile_upload(self):
        """Test 6: Voice Profile Upload - File upload functionality"""
        try:
            # Create a dummy audio file (simulate WAV file)
            audio_data = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x08\x00\x00"
            audio_file = io.BytesIO(audio_data)
            
            # Test voice upload
            files = {
                'audio_file': ('test_voice.wav', audio_file, 'audio/wav')
            }
            data = {
                'name': 'Test Voice Profile'
            }
            
            upload_response = self.session.post(f"{BASE_URL}/voice/upload", files=files, data=data)
            
            if upload_response.status_code != 200:
                self.log_result("Voice Profile Upload", False, f"Upload failed: HTTP {upload_response.status_code}", upload_response.text)
                return False
            
            voice_profile = upload_response.json()
            voice_id = voice_profile["id"]
            self.created_voice_profiles.append(voice_id)
            
            # Verify voice profile structure
            required_fields = ["id", "name", "audio_data", "duration", "created_at"]
            missing_fields = [field for field in required_fields if field not in voice_profile]
            if missing_fields:
                self.log_result("Voice Profile Upload", False, f"Missing fields: {missing_fields}")
                return False
            
            # Test voice profiles list
            list_response = self.session.get(f"{BASE_URL}/voice/profiles")
            if list_response.status_code != 200:
                self.log_result("Voice Profile Upload", False, f"List failed: HTTP {list_response.status_code}")
                return False
            
            voice_profiles = list_response.json()
            if not isinstance(voice_profiles, list):
                self.log_result("Voice Profile Upload", False, "Voice profiles response is not a list")
                return False
            
            # Test voice synthesis (basic)
            synth_response = self.session.post(f"{BASE_URL}/voice/synthesize", params={"text": "Hello, this is a test message"})
            if synth_response.status_code != 200:
                self.log_result("Voice Profile Upload", False, f"Synthesis failed: HTTP {synth_response.status_code}")
                return False
            
            self.log_result("Voice Profile Upload", True, f"Voice upload and synthesis successful. Created voice profile: {voice_id}")
            return True
            
        except Exception as e:
            self.log_result("Voice Profile Upload", False, f"Exception: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete created profiles
        for profile_id in self.created_profiles:
            try:
                response = self.session.delete(f"{BASE_URL}/profiles/{profile_id}")
                if response.status_code == 200:
                    print(f"   ✅ Deleted profile: {profile_id}")
                else:
                    print(f"   ⚠️  Failed to delete profile {profile_id}: HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error deleting profile {profile_id}: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting AI Meeting Assistant Backend Tests")
        print(f"📡 Testing against: {BASE_URL}")
        print("=" * 60)
        
        # Run synchronous tests
        tests = [
            self.test_basic_api_connectivity,
            self.test_meeting_profile_crud,
            self.test_gemini_ai_integration,
            self.test_meeting_session_management,
            self.test_voice_profile_upload
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
                time.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"❌ Test failed with exception: {str(e)}")
                results.append(False)
        
        # Run WebSocket test (async)
        try:
            websocket_result = asyncio.run(self.test_websocket_live_meeting())
            results.append(websocket_result)
        except Exception as e:
            print(f"❌ WebSocket test failed with exception: {str(e)}")
            results.append(False)
        
        # Cleanup
        self.cleanup_test_data()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(results)
        total = len(results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {test_name}")
            if not result["success"]:
                print(f"   Error: {result['message']}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Backend is working correctly.")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed. Check the details above.")
            return False

def main():
    """Main test execution"""
    tester = BackendTester()
    success = tester.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)