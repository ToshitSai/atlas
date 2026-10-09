import sys
from backend.intent_router import classify_research_route, classify_intent
from backend.web_search import search_web, _search_duckduckgo, result_matches_query
from backend.current_info import extract_current_fact_request, answer_current_fact

prompts = [
    'give me sample research paper on fake news detectoon',
    'weather status today',
    'trees',
    'papaya',
    'give me colleges list there in hyderabad'
]

with open('test_output.txt', 'w', encoding='utf-8') as f:
    for p in prompts:
        f.write(f'========================================\n')
        f.write(f'PROMPT: {p}\n')
        route = classify_research_route(p)
        f.write(f'ROUTE: {route.get("mode")} | reason: {route.get("reason")}\n')
        
        intent = classify_intent(p)
        f.write(f'INTENT: {intent}\n')
        
        ci_req = extract_current_fact_request(p)
        f.write(f'CURRENT INFO REQ: {ci_req}\n')
        
        web_res = search_web(p)
        f.write(f'SEARCH_WEB COUNT: {len(web_res)}\n')
        for idx, r in enumerate(web_res):
            f.write(f'  [{idx}] title: {r.get("title")}, url: {r.get("url")}\n')
            f.write(f'       snippet: {r.get("snippet")[:100]}\n')
            f.write(f'       source: {r.get("source")}\n')

print('DONE WROTE FILE')
