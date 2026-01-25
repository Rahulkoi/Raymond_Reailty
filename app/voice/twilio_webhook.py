# from fastapi import APIRouter, Request
# from fastapi.responses import Response
# from urllib.parse import parse_qs

# from app.conversation.manager import ConversationManager

# router = APIRouter()
# cm = ConversationManager()

# @router.post("/voice")
# async def voice_webhook(request: Request):
#     """
#     Twilio Voice Webhook
#     """
#     body = await request.body()
#     data = parse_qs(body.decode())

#     user_speech = data.get("SpeechResult", [None])[0]

#     # If user said something → send to AI
#     if user_speech:
#         ai_response = cm.handle_user_input(user_speech)
#         reply_text = ai_response.get("text", "Can you please repeat?")
#     else:
#         reply_text = (
#             "Hello. I am your AI property assistant. "
#             "Tell me what kind of property you are looking for."
#         )

#     twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
# <Response>
#     <Gather input="speech"
#             timeout="5"
#             speechTimeout="auto"
#             action="/voice"
#             method="POST">
#         <Say voice="alice">{reply_text}</Say>
#     </Gather>

#     <Say voice="alice">
#         I did not hear anything. Goodbye.
#     </Say>
# </Response>
# """

#     return Response(content=twiml, media_type="application/xml")
