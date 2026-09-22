import sys
import json
import os
sys.path.insert(0, os.path.abspath('backend'))
sys.stdout.reconfigure(encoding='utf-8')

from app.services.chat_service import process_chat_message

test_cases = [
    # Hindi
    {'query': 'गेहूं में पीला रतुआ के लक्षण और बचाव बताइए', 'lang': 'hi', 'domain': 'crop_health'},
    {'query': 'धान में खैरा रोग का क्या कारण है?', 'lang': 'hi', 'domain': 'soil_nutrients'},
    {'query': 'पीएम किसान सम्मान निधि में ई-केवाईसी कैसे करें?', 'lang': 'hi', 'domain': 'schemes'},
    # Hinglish
    {'query': 'sarson me maahu pest ka organic control kaise karein?', 'lang': 'hinglish', 'domain': 'crop_health'},
    {'query': 'gehun me pehli sinchai CRI stage par karni chahiye?', 'lang': 'hinglish', 'domain': 'irrigation'},
    {'query': 'makka me fall armyworm ke lakshan kya hain?', 'lang': 'hinglish', 'domain': 'crop_health'},
    # English
    {'query': 'What is the recommended seed treatment for chickpea wilt in Bundelkhand?', 'lang': 'en', 'domain': 'crops'},
    {'query': 'How do hermetic PICS bags protect grain from pulse beetle during storage?', 'lang': 'en', 'domain': 'storage'},
    {'query': 'How can a farmer report localized crop loss under PMFBY insurance?', 'lang': 'en', 'domain': 'insurance'},
    {'query': 'What is the role of Happy Seeder in in-situ paddy straw management?', 'lang': 'en', 'domain': 'mechanization'},
    {'query': 'How to prevent mastitis in Murrah buffalo dairy farming?', 'lang': 'en', 'domain': 'allied'},
    # Live & Guard Routes
    {'query': 'aaj Kanpur mandi me gehun ka rate kya hai?', 'lang': 'hinglish', 'domain': 'live_market'},
    {'query': '15 litre tank me double pesticide kitna milayein?', 'lang': 'hinglish', 'domain': 'safety_refusal'}
]

print("=== STAGE 4 RAG END-TO-END VERIFICATION ===")
success_count = 0
for idx, tc in enumerate(test_cases, 1):
    res = process_chat_message(tc['query'])
    reply = res.get('reply', '')
    sources = res.get('sources', [])
    route = res.get('route', '')
    intent = res.get('intent', '')
    
    # Check leakage
    has_leakage = any(term in reply for term in ['Traceback', 'File "', 'api_key', 'OPENROUTER_API_KEY', 'C:\\Users'])
    
    is_valid = len(reply) > 20 and not has_leakage
    if is_valid:
        success_count += 1
    
    print(f"[{idx}/{len(test_cases)}] {tc['domain']} ({tc['lang']}) -> Intent: {intent} | Route: {route} | Chunks: {len(sources)} | Leakage: {has_leakage} | OK: {is_valid}")

print(f"\nTotal verified: {success_count}/{len(test_cases)}")
assert success_count == len(test_cases)
print("STAGE 4 RAG E2E INTEGRATION: 100% PASSED")
