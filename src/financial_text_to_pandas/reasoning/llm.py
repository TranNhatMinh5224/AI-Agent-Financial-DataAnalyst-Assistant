"""
llm.py — Connect to Qwen LLM and parse outputs.
"""

from __future__ import annotations

import re
import time
from openai import OpenAI

def extract_python_code(text: str) -> str:
    """Extract Python code from LLM Markdown output."""
    if not text:
        return ""
    # 1. Match closed code block ```python ... ```
    pattern = re.compile(r"```(?:python)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
    match = pattern.search(text)
    if match:
        code = match.group(1).strip()
        if code:
            return code
        
    # 2. Match unclosed code block ```python ... (hit max_tokens before closing)
    unclosed_pattern = re.compile(r"```(?:python)?\s*([^\n`].*)", re.DOTALL | re.IGNORECASE)
    match_unclosed = unclosed_pattern.search(text)
    if match_unclosed:
        candidate = match_unclosed.group(1).strip()
        if "result" in candidate:
            return candidate
            
    # 3. Look for explicit result = assignment anywhere in the text
    result_pattern = re.search(r"((?:[a-zA-Z_0-9]+\s*=\s*.*\n?)*result\s*=\s*[^\n]+)", text)
    if result_pattern:
        return result_pattern.group(1).strip()
    
    # 4. If no markdown block, return the whole text
    return text.strip()

def call_llm(prompt: str, llm_config: dict[str, str | float], system_prompt: str = "") -> str:
    """Generic function to call an LLM with a given prompt and system prompt."""
    base_url = llm_config.get("base_url", "http://localhost:11434/v1")
    api_key = llm_config.get("api_key", "ollama")
    model = llm_config.get("model") or llm_config.get("model_name", "qwen2.5-coder:7b")
    temperature = float(llm_config.get("temperature", 0.0))
    max_tokens = int(llm_config.get("max_tokens", 3072))
    
    max_attempts = 4
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            client = OpenAI(base_url=base_url, api_key=api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=90.0,
            )
            
            msg = response.choices[0].message
            raw_response = msg.content
            if not raw_response:
                raw_response = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
                if hasattr(msg, "model_extra") and msg.model_extra:
                    raw_response = raw_response or msg.model_extra.get("reasoning") or msg.model_extra.get("reasoning_content")
                    
            if not raw_response:
                raise ValueError("LLM returned an empty response.")
                
            return raw_response
        except Exception as e:
            last_err = e
            if attempt < max_attempts:
                wait_time = 2 ** attempt
                print(f"[WARN] LLM API call attempt {attempt}/{max_attempts} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"LLM Connection failed after {max_attempts} attempts: {e}")
                raise RuntimeError(f"Chưa kết nối được AI ({model}). Vui lòng kiểm tra lại. Lỗi: {e}")

def generate_pot_code(prompt: str, llm_config: dict[str, str | float]) -> str:
    """Call LLM API to generate PoT Python code."""
    system_prompt = "You are an expert Data Analyst and Python programmer. You must output clean, robust Python code using pandas. Do not use import statements."
    raw_response = call_llm(prompt, llm_config, system_prompt)
    return extract_python_code(raw_response)
