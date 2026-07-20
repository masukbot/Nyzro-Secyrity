"""
Rinox Sentinel - Security Engine
AI Pipeline: Fast Local Checks → OCR → QR → AI Vision → URL Check → Risk Score → Action
"""

import re
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import discord

logger = logging.getLogger("Rinox.Security")


class ScanType(Enum):
    MESSAGE = "message"
    IMAGE = "image"
    ATTACHMENT = "attachment"
    URL = "url"
    USER = "user"
    INVITE = "invite"


class ActionType(Enum):
    NONE = "none"
    DELETE = "delete"
    WARN = "warn"
    TIMEOUT = "timeout"
    KICK = "kick"
    BAN = "ban"
    QUARANTINE = "quarantine"
    MUTE = "mute"
    LOCK_CHANNEL = "lock_channel"
    NOTIFY_STAFF = "notify_staff"
    DM_USER = "dm_user"
    LOG = "log"


@dataclass
class ScanResult:
    """Result of a security scan"""
    scan_type: ScanType
    threat_level: int  # 0-4
    risk_score: int  # 0-100
    confidence: float  # 0.0-1.0
    detected_issues: List[str]
    actions: List[ActionType]
    evidence: Dict[str, Any]
    processing_time_ms: int
    pipeline_stages: List[str]
    
    @property
    def is_threat(self) -> bool:
        return self.risk_score >= 40
        
    @property
    def color(self) -> int:
        if self.risk_score >= 81:
            return 0x8B0000  # Critical
        elif self.risk_score >= 61:
            return 0xED4245  # High
        elif self.risk_score >= 41:
            return 0xFAA61A  # Medium
        elif self.risk_score >= 21:
            return 0xFEE75C  # Low
        return 0x57F287  # Safe


class SecurityEngine:
    """Main security engine with AI pipeline"""
    
    # Known malicious patterns
    MALICIOUS_URLS = [
        r"discord\.gg\/[a-zA-Z0-9]{1,5}",  # Short invites
        r"discordapp\.com\/gift\/[a-zA-Z0-9]+",  # Fake nitro
        r"steamcommunity\.com\/(?!.*steamcommunity)",  # Fake steam
        r"roblox\.com\/(?!.*roblox)",  # Fake roblox
        r"bit\.ly|tinyurl|t\.co|short\.link",  # URL shorteners
    ]
    
    SUSPICIOUS_PATTERNS = [
        r"free\s*nitro",
        r"free\s*robux",
        r"free\s*steam\s*key",
        r"click\s*here\s*to\s*claim",
        r"you\s*won\s*a\s*prize",
        r"verify\s*your\s*account",
        r"login\s*with\s*discord",
        r"\$\d+\s*giveaway",
        r"@everyone\s*@here",
        r"(.)\\1{10,}",  # Repeated characters
    ]
    
    DANGEROUS_EXTENSIONS = [
        ".exe", ".scr", ".bat", ".cmd", ".sh", ".dll",
        ".js", ".vbs", ".ps1", ".wsf", ".hta", ".jar",
        ".apk", ".msi", ".dmg", ".pkg",
    ]
    
    def __init__(self, ai_manager, cache_manager):
        self.ai = ai_manager
        self.cache = cache_manager
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_PATTERNS]
        self._url_patterns = [re.compile(p, re.IGNORECASE) for p in self.MALICIOUS_URLS]
        
    async def scan_message(self, message: discord.Message, 
                         guild_settings: Dict) -> ScanResult:
        """Scan a message through the AI pipeline"""
        import time
        start_time = time.time()
        stages = []
        detected_issues = []
        risk_score = 0
        confidence = 1.0
        
        # Stage 1: Fast Local Checks (Regex, patterns)
        stages.append("local_checks")
        content = message.content or ""
        
        # Check for suspicious patterns
        for pattern in self._compiled_patterns:
            if pattern.search(content):
                detected_issues.append(f"Suspicious pattern detected: {pattern.pattern[:30]}...")
                risk_score += 15
                
        # Check for mass mentions
        mention_count = len(message.mentions) + len(message.role_mentions)
        if mention_count > 5:
            detected_issues.append(f"Mass mention detected ({mention_count} mentions)")
            risk_score += 20
            
        # Stage 2: URL Analysis
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
        if urls:
            stages.append("url_analysis")
            for url in urls:
                url_risk = await self._check_url(url)
                risk_score += url_risk
                if url_risk > 30:
                    detected_issues.append(f"Malicious URL detected: {url[:50]}...")
                    
        # Stage 3: AI Content Analysis (if risk is moderate or high message length)
        if risk_score >= 20 or len(content) > 50:
            stages.append("ai_analysis")
            ai_risk, ai_confidence, ai_issues = await self._ai_analyze_text(content)
            risk_score = max(risk_score, ai_risk)
            confidence = min(confidence, ai_confidence)
            detected_issues.extend(ai_issues)
            
        # Cap risk score
        risk_score = min(risk_score, 100)
        
        # Determine threat level
        threat_level = self._risk_to_threat(risk_score)
        
        # Determine actions
        actions = self._determine_actions(threat_level, guild_settings)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ScanResult(
            scan_type=ScanType.MESSAGE,
            threat_level=threat_level,
            risk_score=risk_score,
            confidence=confidence,
            detected_issues=detected_issues,
            actions=actions,
            evidence={
                "content_preview": content[:500] if content else None,
                "urls_found": urls,
                "mention_count": mention_count,
                "message_id": message.id,
                "channel_id": message.channel.id,
                "author_id": message.author.id,
            },
            processing_time_ms=processing_time,
            pipeline_stages=stages
        )
        
    async def scan_image(self, image_url: str, guild_settings: Dict,
                        message: discord.Message = None) -> ScanResult:
        """Scan an image through the AI pipeline"""
        import time
        start_time = time.time()
        stages = []
        detected_issues = []
        risk_score = 0
        confidence = 1.0
        
        # Stage 1: File type check
        stages.append("file_check")
        
        # Stage 2: OCR (if enabled)
        if guild_settings.get("ocr_enabled", True):
            stages.append("ocr")
            try:
                ocr_text = await self._perform_ocr(image_url)
                if ocr_text:
                    # Check OCR text for suspicious content
                    for pattern in self._compiled_patterns:
                        if pattern.search(ocr_text):
                            detected_issues.append(f"Suspicious text in image: {pattern.pattern[:30]}...")
                            risk_score += 20
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
                
        # Stage 3: QR Code Scan
        stages.append("qr_scan")
        try:
            qr_data = await self._scan_qr(image_url)
            if qr_data:
                detected_issues.append(f"QR code found: {qr_data[:100]}")
                url_risk = await self._check_url(qr_data)
                risk_score += url_risk
        except Exception as e:
            logger.warning(f"QR scan failed: {e}")
            
        # Stage 4: AI Vision Analysis
        if guild_settings.get("vision_enabled", True):
            stages.append("ai_vision")
            try:
                vision_result = await self._ai_vision_analysis(image_url)
                risk_score = max(risk_score, vision_result.get("risk_score", 0))
                confidence = vision_result.get("confidence", 0.8)
                detected_issues.extend(vision_result.get("issues", []))
            except Exception as e:
                logger.warning(f"AI vision failed: {e}")
                
        # Cap risk score
        risk_score = min(risk_score, 100)
        threat_level = self._risk_to_threat(risk_score)
        actions = self._determine_actions(threat_level, guild_settings)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        evidence = {"image_url": image_url}
        if message:
            evidence.update({
                "message_id": message.id,
                "channel_id": message.channel.id,
                "author_id": message.author.id,
            })
            
        return ScanResult(
            scan_type=ScanType.IMAGE,
            threat_level=threat_level,
            risk_score=risk_score,
            confidence=confidence,
            detected_issues=detected_issues,
            actions=actions,
            evidence=evidence,
            processing_time_ms=processing_time,
            pipeline_stages=stages
        )
        
    async def scan_attachment(self, attachment: discord.Attachment,
                              guild_settings: Dict) -> ScanResult:
        """Scan a file attachment"""
        import time
        start_time = time.time()
        stages = ["file_check"]
        detected_issues = []
        risk_score = 0
        
        filename = attachment.filename.lower()
        
        # Check file extension
        for ext in self.DANGEROUS_EXTENSIONS:
            if filename.endswith(ext):
                detected_issues.append(f"Dangerous file type: {ext}")
                risk_score += 50
                
        # Check for double extensions (e.g., image.jpg.exe)
        if filename.count(".") > 1:
            detected_issues.append("Suspicious double extension detected")
            risk_score += 30
            
        # Check file size (suspicious if very small executable)
        if attachment.size < 1024 and any(filename.endswith(ext) for ext in self.DANGEROUS_EXTENSIONS):
            detected_issues.append("Suspiciously small executable file")
            risk_score += 20
            
        threat_level = self._risk_to_threat(risk_score)
        actions = self._determine_actions(threat_level, guild_settings)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ScanResult(
            scan_type=ScanType.ATTACHMENT,
            threat_level=threat_level,
            risk_score=risk_score,
            confidence=0.95,
            detected_issues=detected_issues,
            actions=actions,
            evidence={
                "filename": attachment.filename,
                "size": attachment.size,
                "content_type": attachment.content_type,
                "url": attachment.url,
            },
            processing_time_ms=processing_time,
            pipeline_stages=stages
        )
        
    async def scan_user(self, member: discord.Member, 
                       guild_settings: Dict) -> ScanResult:
        """Scan a user for suspicious activity"""
        import time
        start_time = time.time()
        stages = ["user_profile"]
        detected_issues = []
        risk_score = 0
        
        # Check account age
        account_age_days = (datetime.utcnow() - member.created_at).days
        if account_age_days < 1:
            detected_issues.append("Account created less than 1 day ago")
            risk_score += 25
        elif account_age_days < 7:
            detected_issues.append("Account created less than 7 days ago")
            risk_score += 15
            
        # Check avatar (default avatar = slightly suspicious)
        if member.avatar is None:
            detected_issues.append("No custom avatar")
            risk_score += 5
            
        # Check username patterns
        username = member.name.lower()
        if any(word in username for word in ["bot", "admin", "moderator", "support"]):
            detected_issues.append("Username contains suspicious keywords")
            risk_score += 10
            
        # Check for similar names (impersonation)
        # This would require checking against staff names
        
        threat_level = self._risk_to_threat(risk_score)
        actions = self._determine_actions(threat_level, guild_settings)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ScanResult(
            scan_type=ScanType.USER,
            threat_level=threat_level,
            risk_score=risk_score,
            confidence=0.7,
            detected_issues=detected_issues,
            actions=actions,
            evidence={
                "user_id": member.id,
                "username": member.name,
                "account_age_days": account_age_days,
                "joined_at": str(member.joined_at),
            },
            processing_time_ms=processing_time,
            pipeline_stages=stages
        )
        
    async def _check_url(self, url: str) -> int:
        """Check URL reputation, returns risk score addition"""
        risk = 0
        
        # Check cache first
        if self.cache:
            cached = await self.cache.get_url_reputation(url)
            if cached:
                return cached.get("risk_score", 0)
                
        # Check for URL shorteners
        for pattern in self._url_patterns:
            if pattern.search(url):
                risk += 20
                
        # Check for suspicious TLDs
        suspicious_tlds = [".tk", ".ml", ".ga", ".cf", ".gq"]
        if any(url.endswith(tld) for tld in suspicious_tlds):
            risk += 15
            
        # Cache result
        if self.cache:
            await self.cache.set_url_reputation(url, {"risk_score": risk})
            
        return risk
        
    async def _ai_analyze_text(self, content: str) -> Tuple[int, float, List[str]]:
        """Use AI to analyze text content"""
        if not self.ai or not content:
            return 0, 1.0, []
            
        system_prompt = """You are a security analysis AI. Analyze the following Discord message for:
1. Spam/Advertisement
2. Phishing attempts
3. Scams (crypto, nitro, steam, roblox)
4. Toxic/Hate speech
5. NSFW content
6. Mass mention spam

Respond ONLY in this exact format:
RISK_SCORE: [0-100]
CONFIDENCE: [0.0-1.0]
ISSUES:
- [issue 1]
- [issue 2]
..."""

        messages = [{"role": "user", "content": content[:2000]}]
        
        response = await self.ai.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=500
        )
        
        if not response.success:
            return 0, 0.5, ["AI analysis failed"]
            
        # Parse response
        text = response.content
        risk_score = 0
        confidence = 0.5
        issues = []
        
        try:
            for line in text.split("\n"):
                if line.startswith("RISK_SCORE:"):
                    risk_score = int(line.split(":")[1].strip())
                elif line.startswith("CONFIDENCE:"):
                    confidence = float(line.split(":")[1].strip())
                elif line.startswith("-"):
                    issues.append(line[1:].strip())
        except:
            pass
            
        return risk_score, confidence, issues
        
    async def _perform_ocr(self, image_url: str) -> str:
        """Perform OCR on image"""
        try:
            import pytesseract
            from PIL import Image
            import aiohttp
            import io
            
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        image = Image.open(io.BytesIO(image_data))
                        text = pytesseract.image_to_string(image)
                        return text
        except Exception as e:
            logger.warning(f"OCR error: {e}")
            
        return ""
        
    async def _scan_qr(self, image_url: str) -> str:
        """Scan QR code from image"""
        try:
            from pyzbar.pyzbar import decode
            from PIL import Image
            import aiohttp
            import io
            
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        image = Image.open(io.BytesIO(image_data))
                        decoded = decode(image)
                        if decoded:
                            return decoded[0].data.decode("utf-8")
        except Exception as e:
            logger.warning(f"QR scan error: {e}")
            
        return ""
        
    async def _ai_vision_analysis(self, image_url: str) -> Dict:
        """Analyze image with AI vision"""
        if not self.ai:
            return {"risk_score": 0, "confidence": 1.0, "issues": []}
            
        prompt = """Analyze this image for security threats:
1. Fake login pages (Discord, Steam, Roblox)
2. QR codes leading to malicious sites
3. Fake giveaways/prizes
4. Adult/NSFW content
5. Violence/weapons
6. Scam advertisements
7. Malware indicators

Respond in format:
RISK_SCORE: [0-100]
CONFIDENCE: [0.0-1.0]
ISSUES:
- [issue]
"""
        
        response = await self.ai.vision(image_url, prompt)
        
        if not response.success:
            return {"risk_score": 0, "confidence": 0.5, "issues": ["Vision analysis failed"]}
            
        text = response.content
        risk_score = 0
        confidence = 0.5
        issues = []
        
        try:
            for line in text.split("\n"):
                if line.startswith("RISK_SCORE:"):
                    risk_score = int(line.split(":")[1].strip())
                elif line.startswith("CONFIDENCE:"):
                    confidence = float(line.split(":")[1].strip())
                elif line.startswith("-"):
                    issues.append(line[1:].strip())
        except:
            pass
            
        return {"risk_score": risk_score, "confidence": confidence, "issues": issues}
        
    def _risk_to_threat(self, risk_score: int) -> int:
        """Convert risk score to threat level"""
        if risk_score >= 81:
            return 4  # Critical
        elif risk_score >= 61:
            return 3  # High
        elif risk_score >= 41:
            return 2  # Medium
        elif risk_score >= 21:
            return 1  # Low
        return 0  # Safe
        
    def _determine_actions(self, threat_level: int, 
                          guild_settings: Dict) -> List[ActionType]:
        """Determine actions based on threat level"""
        actions = [ActionType.LOG]
        
        if threat_level >= 4:  # Critical
            actions.extend([
                ActionType.DELETE,
                ActionType.BAN,
                ActionType.NOTIFY_STAFF
            ])
        elif threat_level >= 3:  # High
            actions.extend([
                ActionType.DELETE,
                ActionType.TIMEOUT,
                ActionType.NOTIFY_STAFF
            ])
        elif threat_level >= 2:  # Medium
            actions.extend([
                ActionType.DELETE,
                ActionType.WARN,
                ActionType.NOTIFY_STAFF
            ])
        else:  # Low or Safe
            actions.extend([
                ActionType.WARN,
                ActionType.LOG
            ])
            
        return actions
