import os
from mistralai import Mistral
import re
import subprocess
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")
agent_id = os.getenv("AGENT_ID")

client = Mistral(api_key=api_key)

def run_javascript_agent(query):
    """
    Sends a user query to a JavaScript agent and returns the response.

    Args:
        query (str): The user query to be sent to the JavaScript agent.

    Returns:
        str: The response content from the JavaScript agent.
    """
    print("### Run JavaScript agent")
    print(f"User query: {query}")
    try:
        response = client.agents.complete(
            agent_id=agent_id,
            messages=[
                {
                    "role": "user",
                    "content": query
                },
            ]
        )
        print("Full Response:", response)  # Print the full response object
        result = response.choices[0].message.content
        print("Response Content:", result)  # Print the response content
        return result
    except Exception as e:
        print(f"Request failed: {e}. Please check your request.")
        return None

def extract_pattern(text, pattern):
    """
    Extracts a pattern from the given text.

    Args:
        text (str): The text to search within.
        pattern (str): The regex pattern to search for.

    Returns:
        str: The extracted pattern or None if not found.
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

    Args:
        result (str): The response content from the JavaScript agent.

    Returns:
        tuple: A tuple containing the extracted JavaScript function, test function, and a retry flag.
    """
    if result is None:
        print("Result is None. Skipping extraction.")
        return None, None, True

    retry = False
    print("### Extracting JavaScript code")
    js_function = extract_pattern(result, r'```javascript\n(.*?)```')
    if not js_function:
        retry = True
        print("JavaScript function failed to generate or wrong output format. Setting retry to True.")

    print("### Extracting test case")
    test_function = extract_pattern(result, r'```javascript\n(.*?)```')
    if not test_function:
        retry = True
        print("Test function failed to generate or wrong output format. Setting retry to True.")

    return js_function, test_function, retry

def check_code(js_function, test_function):
    """
    Executes the JavaScript function and its test case using Node.js, and checks for any errors.

    Args:
        js_function (str): The JavaScript function to be executed.
        test_function (str): The test case to be executed.

    Returns:
        bool: A flag indicating whether the code execution needs to be retried.
    """
    retry = False
    try:
        # Write the JavaScript function to a file
        with open("temp_function.js", "w") as f:
            f.write(js_function)

        # Execute the JavaScript function using Node.js
        subprocess.run(["node", "temp_function.js"], check=True)
        print("Code executed successfully.")

        # Write the test function to a file
        with open("temp_test.js", "w") as f:
            f.write(test_function)

        # Execute the test function using Node.js
        subprocess.run(["node", "temp_test.js"], check=True)
        print("Code passed test case.")
    except subprocess.CalledProcessError:
        print("Code or test failed.")
        retry = True
        print("Setting retry to True")
    return retry

def run_workflow(query):
    """
    Runs the complete workflow to generate, extract, and validate JavaScript code.

    Args:
        query (str): The user query to be processed.
    """
    # Modify the query to explicitly ask for JavaScript code
    query = f"{query} in JavaScript"

    print("### ENTER WORKFLOW")
    i = 0
    max_retries = 3
    retry = True  # just to get it started
    while i < max_retries and retry:
        print(f"TRY # {i}")
        i += 1
        result = run_javascript_agent(query)
        if result is None:
            print("Result is None. Skipping this iteration.")
            continue
        js_function, test_function, retry = extract_code(result)
        if js_function and test_function:
            retry = check_code(js_function, test_function)
        else:
            print("Skipping code check due to missing function or test case.")

    if not retry:
        print(f"Validated JavaScript function: ```{js_function}```")
    print("### EXIT WORKFLOW")

run_workflow("How can I remove duplicates from a list")
