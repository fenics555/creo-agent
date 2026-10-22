import subprocess
import json
import os

def run_test():
    mock_file = r"D:\AI\tools\agent\creo_reverse_engineering\work\complex_mock.bin"
    output_json = r"D:\AI\tools\agent\creo_reverse_engineering\work\test_output.json"
    log_file = r"D:\AI\log\creo_reverse_engineering\test_results.log"
    parser_script = r"D:\AI\tools\agent\creo_reverse_engineering\creo_mapping_table_parser.py"

    print("--- Running Parser Test ---")
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Run the parser
    result = subprocess.run(
        ["python", parser_script, mock_file, output_json],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        error_msg = f"TEST FAILED: Parser exited with error.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        print(error_msg)
        with open(log_file, "a") as f:
            f.write(error_msg + "\n")
        return

    print(result.stdout)

    # Verify the results
    if not os.path.exists(output_json):
        error_msg = "TEST FAILED: Output JSON was not created."
        print(error_msg)
        with open(log_file, "a") as f:
            f.write(error_msg + "\n")
        return

    with open(output_json, 'r') as f:
        parsed_data = json.load(f)

    # Extract the actual list from the dictionary
    mapping_entries = parsed_data.get("mapping_table", [])

    # Expected data from complex_mock.bin
    expected_entries = [
        {"name": "Param_Mass", "value": 12.345},
        {"name": "Param_Vol", "value": 0.987},
        {"name": "Fixture_Name", "value": "Fixture_10X1-D12"}
    ]

    success = True
    found_count = 0
    for expected in expected_entries:
        found = False
        for actual in mapping_entries:
            # Using almost equal for floats
            if actual.get("name") == expected["name"]:
                if isinstance(expected["value"], float):
                    if abs(actual.get("value", 0) - expected["value"]) < 0.001:
                        found = True
                else:
                    if actual.get("value") == expected["value"]:
                        found = True
                
                if found:
                    found_count += 1
                    break
        if not found:
            print(f"[-] Missing or incorrect entry: {expected}")
            success = False

    if success and found_count == len(expected_entries):
        msg = "TEST PASSED: All expected entries found in parsed data."
        print(msg)
        with open(log_file, "a") as f:
            f.write(msg + "\n")
    else:
        msg = f"TEST FAILED: Found {found_count}/{len(expected_entries)} expected entries."
        print(msg)
        with open(log_file, "a") as f:
            f.write(msg + "\n")

if __name__ == "__main__":
    run_test()
