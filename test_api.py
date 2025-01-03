from openai import OpenAI
import os
from decouple import config

# Test with API key from .env
API_KEY = config('OPENAI_API_KEY')
print(f"Using API key: {API_KEY[:10]}...")
client = OpenAI(api_key=API_KEY)

try:
    # Test embeddings
    print('Testing embeddings...')
    response = client.embeddings.create(
        model='text-embedding-ada-002',
        input='Hello world'
    )
    print('✅ Embeddings API working!')
    
    # Test chat completion
    print('\nTesting chat completion...')
    response = client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': 'Say hello'}],
        max_tokens=10
    )
    print('✅ Chat API working!')
    
except Exception as e:
    print('❌ Error:', str(e)) 