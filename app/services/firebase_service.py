import logging
import os
import firebase_admin
from firebase_admin import credentials, auth, messaging
from app.config.settings import settings

logger = logging.getLogger("namma_bus")

class FirebaseService:
    _initialized = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return
        
        creds_path = settings.FIREBASE_CREDENTIALS_PATH
        if os.path.exists(creds_path):
            try:
                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info("Firebase: Admin SDK initialized successfully.")
            except Exception as e:
                logger.error(f"Firebase: Failed to initialize Admin SDK: {e}")
        else:
            logger.warning(
                f"Firebase: Credentials file not found at {creds_path}. "
                "Firebase services will run in MOCK mode."
            )

    @classmethod
    def verify_token(cls, id_token: str) -> dict:
        """Verifies a Firebase ID token. Fallbacks to mock if Firebase SDK is uninitialized."""
        cls.initialize()
        
        # Mock mode fallback for local test suite ease
        if not cls._initialized:
            if id_token.startswith("mock-token-"):
                email = f"{id_token.replace('mock-token-', '')}@example.com"
                return {
                    "uid": f"firebase-uid-{id_token}",
                    "email": email,
                    "name": "Firebase Mock User"
                }
            raise ValueError("Firebase: Verification failed (App is running in Mock Mode. Pass a mock-token- prefix for auth testing).")
            
        try:
            decoded_token = auth.verify_id_token(id_token)
            return {
                "uid": decoded_token.get("uid"),
                "email": decoded_token.get("email"),
                "name": decoded_token.get("name", "Firebase User")
            }
        except Exception as e:
            logger.error(f"Firebase: Token verification failed: {e}")
            raise ValueError(f"Firebase: Token verification failed: {e}")

    @classmethod
    async def send_multicast_notification(cls, tokens: list[str], title: str, body: str, data: dict = None) -> int:
        """Broadcasts push notification to list of FCM tokens. Returns success count."""
        cls.initialize()
        if not cls._initialized:
            logger.info(f"Firebase Mock FCM: Sending notification '{title}' to {len(tokens)} tokens.")
            return len(tokens)

        if not tokens:
            return 0
            
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                tokens=tokens
            )
            response = messaging.send_each_for_multicast(message)
            logger.info(f"Firebase FCM: Successfully sent {response.success_count} notifications.")
            return response.success_count
        except Exception as e:
            logger.error(f"Firebase FCM: Failed to send multicast message: {e}")
            return 0
