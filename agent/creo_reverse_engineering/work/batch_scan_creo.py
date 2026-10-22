import subprocess
import os
import json

def batch_scan(file_list, parser_script, output_base_dir):
    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)

    results_summary = []

    for file_path in file_list:
        print(f"Processing: {file_path}")
        # Generate output filename based on the input filename
        base_name = os.path.basename(file_path).replace('.', '_')
        output_json = os.path.join(output_base_dir, f"{base_name}.json")
        
        result = subprocess.run(
            ["python", parser_script, file_path, output_json],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            # Check if JSON was actually created and has content
            if os.path.exists(output_json):
                with open(output_json, 'r') as f:
                    try:
                        data = json.load(f)
                        if len(data) > 0:
                            results_summary.append({
                                "file": file_path,
                                "status": "SUCCESS",
                                "entries_found": len(data),
                                "output": output_json
                            })
                        else:
                            results_summary.append({
                                "file": file_path,
                                "status": "SUCCESS_BUT_EMPTY",
                                "output": output_json
                            })
                    except json.JSONDecodeError:
                        results_summary.append({
                            "file": file_path,
                            "status": "SUCCESS_BUT_INVALID_JSON",
                            "output": output_json
                        })
            else:
                results_summary.append({
                    "file": file_path,
                    "status": "SUCCESS_BUT_NO_OUTPUT_FILE",
                })
        else:
            results_summary.append({
                "file": file_path,
                "status": "FAILED",
                "error": result.stderr.strip()
            })

    # Save summary
    summary_file = os.path.join(output_base_dir, "scan_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(results_summary, f, indent=4)
    
    return results_summary, summary_file

if __name__ == "__main__":
    files_to_scan = [
        r"Z:\PTC\Work\000_51 DF Держатели форм\000_1 DF-STP2 СТАНДАРТНЫЕ ИЗДЕЛИЯ ДФ\df-stp-vz-z.prt.1",
        r"Z:\PTC\Work\000_51 DF Держатели форм\000_1 DF-STP2 СТАНДАРТНЫЕ ИЗДЕЛИЯ ДФ\df-stp2-gdf.prt.1"
    ]
    parser = r"D:\AI\tools\agent\creo_reverse_engineering\creo_mapping_table_parser.py"
    output_dir = r"D:\AI\log\creo_reverse_engineering\scan_results"
    
    summary, summary_path = batch_scan(files_to_scan, parser, output_dir)
    print(f"\nScan complete. Summary saved to: {summary_path}")
    print(json.dumps(summary, indent=2))
