from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import json
import asyncio
from datetime import datetime
from emergentintegrations.llm.chat import LlmChat, UserMessage
import websockets
import base64
import io


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class MeetingProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    personality: str
    response_style: str
    meeting_topics: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = "default"

class MeetingProfileCreate(BaseModel):
    name: str
    role: str
    personality: str
    response_style: str
    meeting_topics: List[str] = []

class MeetingSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    profile_id: str
    participants: List[str] = []
    status: str = "active"  # active, paused, ended
    conversation_history: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = "default"

class MeetingSessionCreate(BaseModel):
    title: str
    profile_id: str
    participants: List[str] = []

class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    speaker_name: Optional[str] = None

class VoiceProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    audio_data: str  # base64 encoded
    duration: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = "default"

class AIResponse(BaseModel):
    message: str
    confidence: float
    response_type: str  # answer, question, acknowledgment
    audio_url: Optional[str] = None

# Global chat instances store
chat_instances: Dict[str, LlmChat] = {}

# Utility functions
async def get_ai_chat(session_id: str, profile: MeetingProfile) -> LlmChat:
    """Get or create AI chat instance for session"""
    if session_id not in chat_instances:
        system_message = f"""You are {profile.name}, a {profile.role}. 
        Personality: {profile.personality}
        Response style: {profile.response_style}
        
        You are attending a meeting on behalf of someone. Your responses should be:
        - Professional and contextual
        - Brief but meaningful (2-3 sentences max)
        - Appropriate for the meeting context
        - Reflect the personality and role described
        
        Meeting topics you're familiar with: {', '.join(profile.meeting_topics)}
        
        Important: Always respond as if you're the person attending the meeting, not an AI assistant."""
        
        chat_instances[session_id] = LlmChat(
            api_key=os.environ.get('GEMINI_API_KEY'),
            session_id=session_id,
            system_message=system_message
        ).with_model("gemini", "gemini-2.0-flash").with_max_tokens(2048)
    
    return chat_instances[session_id]

# API Routes
@api_router.get("/")
async def root():
    return {"message": "AI Meeting Assistant API"}

# Meeting Profiles
@api_router.post("/profiles", response_model=MeetingProfile)
async def create_profile(profile: MeetingProfileCreate):
    profile_dict = profile.dict()
    profile_obj = MeetingProfile(**profile_dict)
    await db.meeting_profiles.insert_one(profile_obj.dict())
    return profile_obj

@api_router.get("/profiles", response_model=List[MeetingProfile])
async def get_profiles():
    profiles = await db.meeting_profiles.find({"user_id": "default"}).to_list(100)
    return [MeetingProfile(**profile) for profile in profiles]

@api_router.get("/profiles/{profile_id}", response_model=MeetingProfile)
async def get_profile(profile_id: str):
    profile = await db.meeting_profiles.find_one({"id": profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return MeetingProfile(**profile)

@api_router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    result = await db.meeting_profiles.delete_one({"id": profile_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deleted"}

# Meeting Sessions
@api_router.post("/sessions", response_model=MeetingSession)
async def create_session(session: MeetingSessionCreate):
    # Verify profile exists
    profile = await db.meeting_profiles.find_one({"id": session.profile_id})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    session_dict = session.dict()
    session_obj = MeetingSession(**session_dict)
    await db.meeting_sessions.insert_one(session_obj.dict())
    return session_obj

@api_router.get("/sessions", response_model=List[MeetingSession])
async def get_sessions():
    sessions = await db.meeting_sessions.find({"user_id": "default"}).sort("created_at", -1).to_list(100)
    return [MeetingSession(**session) for session in sessions]

@api_router.get("/sessions/{session_id}", response_model=MeetingSession)
async def get_session(session_id: str):
    session = await db.meeting_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return MeetingSession(**session)

@api_router.put("/sessions/{session_id}/status")
async def update_session_status(session_id: str, status: str):
    result = await db.meeting_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Status updated"}

# Chat functionality
@api_router.post("/sessions/{session_id}/chat", response_model=AIResponse)
async def chat_with_ai(session_id: str, message: str):
    # Get session and profile
    session = await db.meeting_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    profile = await db.meeting_profiles.find_one({"id": session["profile_id"]})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    try:
        # Get AI chat instance
        chat = await get_ai_chat(session_id, MeetingProfile(**profile))
        
        # Send message to AI
        user_message = UserMessage(text=message)
        ai_response = await chat.send_message(user_message)
        
        # Store conversation in session
        conversation_entry = {
            "user_message": message,
            "ai_response": ai_response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await db.meeting_sessions.update_one(
            {"id": session_id},
            {"$push": {"conversation_history": conversation_entry}}
        )
        
        return AIResponse(
            message=ai_response,
            confidence=0.9,
            response_type="answer"
        )
    
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate response")

# Voice functionality (basic)
@api_router.post("/voice/upload", response_model=VoiceProfile)
async def upload_voice(name: str = Form(...), audio_file: UploadFile = File(...)):
    """Upload voice sample for future voice cloning"""
    try:
        # Read and encode audio file
        audio_content = await audio_file.read()
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        voice_profile = VoiceProfile(
            name=name,
            audio_data=audio_base64,
            duration=10.0  # Placeholder
        )
        
        await db.voice_profiles.insert_one(voice_profile.dict())
        return voice_profile
    
    except Exception as e:
        logging.error(f"Voice upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload voice")

@api_router.get("/voice/profiles", response_model=List[VoiceProfile])
async def get_voice_profiles():
    profiles = await db.voice_profiles.find({"user_id": "default"}).to_list(10)
    return [VoiceProfile(**profile) for profile in profiles]

@api_router.post("/voice/synthesize")
async def synthesize_voice(text: str, voice_profile_id: Optional[str] = None):
    """Synthesize voice - currently returns text for TTS, can be upgraded to ElevenLabs"""
    return {
        "text": text,
        "voice_id": voice_profile_id,
        "audio_url": None,  # Placeholder for future voice synthesis
        "message": "Text ready for browser TTS. Upgrade to ElevenLabs for voice cloning."
    }

# WebSocket for real-time meeting simulation
@api_router.websocket("/sessions/{session_id}/live")
async def websocket_meeting(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        # Get session and profile
        session = await db.meeting_sessions.find_one({"id": session_id})
        if not session:
            await websocket.send_json({"error": "Session not found"})
            return
        
        profile = await db.meeting_profiles.find_one({"id": session["profile_id"]})
        if not profile:
            await websocket.send_json({"error": "Profile not found"})
            return
        
        await websocket.send_json({
            "type": "connected",
            "message": f"Connected to meeting as {profile['name']}",
            "session_id": session_id
        })
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # Process incoming message and generate AI response
                message = data.get("content", "")
                speaker = data.get("speaker", "Unknown")
                
                try:
                    chat = await get_ai_chat(session_id, MeetingProfile(**profile))
                    user_message = UserMessage(text=f"{speaker}: {message}")
                    ai_response = await chat.send_message(user_message)
                    
                    # Send AI response back
                    await websocket.send_json({
                        "type": "ai_response",
                        "content": ai_response,
                        "speaker": profile["name"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to generate response: {str(e)}"
                    })
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()