import json
from datetime import datetime
from pathlib import Path


class IntegrationTestReportGenerator:
    """Generate comprehensive integration test reports"""

    def __init__(self, report_file: Path):
        self.report_file = report_file

    def generate_html_report(self) -> str:
        """Generate HTML report from test results"""
        with open(self.report_file) as f:
            data = json.load(f)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Crawling Integration Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .phase {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .success {{ border-left: 5px solid #4CAF50; }}
                .failure {{ border-left: 5px solid #f44336; }}
                .summary {{ background: #e3f2fd; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Crawling System Integration Test Report</h1>
                <p>Generated: {datetime.fromtimestamp(data['timestamp'])}</p>
                <p>Total Duration: {data['total_duration']:.2f} seconds</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <p>Passed: {data['summary']['passed_phases']}/{data['summary']['total_phases']} phases</p>
            </div>

            <h2>Phase Details</h2>
        """

        for phase_name, result in data["phases"].items():
            status_class = "success" if result.get("success") else "failure"
            status_text = "PASSED" if result.get("success") else "FAILED"

            html += f"""
            <div class="phase {status_class}">
                <h3>{phase_name} - {status_text}</h3>
                <p>Duration: {result.get('duration', 0):.2f} seconds</p>
                {f'<pre>{result["stderr"]}</pre>' if not result.get('success') else ''}
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    def save_html_report(self, output_path: Path):
        """Save HTML report to file"""
        html = self.generate_html_report()
        with open(output_path, "w") as f:
            f.write(html)
