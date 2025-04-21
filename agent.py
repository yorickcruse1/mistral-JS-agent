import os
import re
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from mistralai import Mistral

# Load environment variables from the .env file
load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")
agent_id = os.getenv("AGENT_ID")

client = Mistral(api_key=api_key)

def log_message(message, level="INFO"):
    """
    Logs a message to the terminal with a timestamp and level.

    Args:
        message (str): The message to log.
        level (str): The log level (e.g., INFO, WARNING, ERROR).
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    level = level.upper()
    print(f"[{timestamp}] [{level}] {message}")

def run_javascript_agent(query):
    """
    Sends a user query to a JavaScript agent and returns the response.
    """
    log_message("### Run JavaScript agent")
    log_message(f"User query: {query}")
    try:
        response = client.agents.complete(
            agent_id=agent_id,
            messages=[{"role": "user", "content": query}]
        )
        result = response.choices[0].message.content
        log_message(result)
        return result
    except Exception as e:
        log_message(f"Request failed: {e}. Please check your request.", level="ERROR")
        return None

def extract_pattern(text, pattern):
    """
    Extracts a pattern from the given text.
    """
    if text is None:
        return None
    match = re.search(pattern, text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def extract_code(result):
    """
    Extracts JavaScript function and test case from the response content.
    """
    if result is None:
        log_message("Result is None. Skipping extraction.", level="WARNING")
        return None, None, True

    retry = False
    log_message("### Extracting JavaScript code")
    js_function = extract_pattern(result, r'## Javascript function\s*(.*?)## Test case')
    if not js_function:
        retry = True
        log_message("JavaScript function failed to generate or wrong output format. Setting retry to True.", level="WARNING")

    log_message("### Extracting test case")
    test_function = extract_pattern(result, r'Test case\s*(.*)')
    if not test_function:
        retry = True
        log_message("Test function failed to generate or wrong output format. Setting retry to True.", level="WARNING")

    return js_function, test_function, retry

def check_code(js_function, test_function):
    """
    Executes the JavaScript function and its test case using Node.js.
    """
    retry = False
    try:
        # Log the JavaScript function
        log_message("Executing JavaScript Function:\n```\n" + js_function + "\n```")

        with open("temp_function.js", "w") as f:
            f.write(js_function)

        subprocess.run(["node", "temp_function.js"], check=True)
        log_message("Code executed successfully.")

        # Log the test function
        log_message("Executing Test Function:\n```\n" + test_function + "\n```")

        with open("temp_test.js", "w") as f:
            f.write(test_function)

        subprocess.run(["node", "temp_test.js"], check=True)
        log_message("Code passed test case.")
    except subprocess.CalledProcessError:
        log_message("Code or test failed.", level="ERROR")
        retry = True
        log_message("Setting retry to True", level="WARNING")
    return retry

def run_workflow(query):
    """
    Runs the complete workflow to generate, extract, and validate JavaScript code.
    """
    query = f"{query} in JavaScript"
    log_message("### ENTER WORKFLOW")
    i = 0
    max_retries = 3
    retry = True
    while i < max_retries and retry:
        log_message(f"TRY # {i}")
        i += 1
        result = run_javascript_agent(query)
        if result is None:
            log_message("Result is None. Skipping this iteration.", level="WARNING")
            continue
        js_function, test_function, retry = extract_code(result)
        if js_function and test_function:
            retry = check_code(js_function, test_function)
        else:
            log_message("Skipping code check due to missing function or test case.", level="WARNING")

    if not retry:
        log_message(f"Validated JavaScript function:\n```\n{js_function}\n```")
    log_message("### EXIT WORKFLOW")

if __name__ == "__main__":
    # Prompt the user for input
    user_query = input("Enter your query: ")
    run_workflow(user_query)
