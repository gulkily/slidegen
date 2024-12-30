# begin generate_slides.py
import os
import re
import subprocess
import sys
import argparse
from pathlib import Path

def parse_config(file_path):
	with open(file_path, 'r', encoding='utf-8') as f:
		content = f.read().strip()

	# Extract course title - look for various formats
	title_patterns = [
		r"Course Title:\s*(.*?)(?:\n|$)",  # Standard format
		r"Title:\s*(.*?)(?:\n|$)",         # Shorter format
		r"^#\s*(.*?)(?:\n|$)",             # Markdown H1 format
		r"^=+\s*(.*?)\s*=+\s*$"            # Underlined format
	]

	course_title = None
	for pattern in title_patterns:
		match = re.search(pattern, content, re.MULTILINE)
		if match:
			course_title = match.group(1).strip()
			break

	if not course_title:
		# If no title found, use first non-empty line
		course_title = next((line.strip() for line in content.split('\n')
						   if line.strip()), "Untitled Course")

	# Extract topics using various patterns
	topics = []
	lines = content.split('\n')

	# Skip header section (everything before first blank line)
	content_start = 0
	for i, line in enumerate(lines):
		if not line.strip():
			content_start = i + 1
			break

	for line in lines[content_start:]:
		line = line.strip()
		if not line:
			continue

		# Skip common section headers
		if re.match(r'^(Part|Section|Module|Chapter)\s+\d+:', line, re.I):
			continue

		# Try various content patterns
		content = None
		patterns = [
			r'^\d+\.\s*(.*)',           # Numbered: "1. Topic"
			r'^[-*•]\s*(.*)',           # Bullet points
			r'^\([A-Z]\)\s*(.*)',       # Letter bullets: "(A) Topic"
			r'(?:Topic|Session):\s*(.*)',# Labeled lines
		]

		for pattern in patterns:
			match = re.match(pattern, line)
			if match:
				content = match.group(1).strip()
				break

		# If no pattern matched but line has content, include it
		if not content and line:
			# Skip common headers/labels
			if not re.match(r'^(Overview|Summary|Notes?|Objectives?):', line, re.I):
				content = line

		if content:
			topics.append(content)

	return course_title, topics

def generate_slide_prompt(course_title, summary_stack, topic):
	return f"""
You are preparing a series of lecture slides for a course titled "{course_title}".

So far, these are the summaries of previous slides:
{summary_stack}

Now please create the next slide. The next slide should cover: "{topic}"

Important presentation guidelines:
- Use a large font size (minimum 24pt equivalent in CSS)
- Limit content to 7-8 bullet points maximum per slide
- Keep text concise - aim for 20-30 words per bullet point maximum
- Use <style> tags to enforce proper sizing
- If content exceeds these limits, indicate it should be split into multiple slides with "<!--SPLIT_SLIDE_HERE-->" comment

If you need clarification about the topic, respond with exactly "TOPIC_CLARIFICATION_NEEDED" and nothing else.

Otherwise, please return only valid HTML that fits into the `{{SLIDE_CONTENT}}` section of the given template. Include a heading and some explanatory text using HTML elements like <h2>, <p>, <ul>, <li>, etc., as needed.

Even if you're not completely sure about some aspects of the topic, please provide your best attempt at creating informative slide content based on your current knowledge. Focus on the key concepts you're most confident about.
"""

def summarize_slide_prompt(slide_content):
	# A simple prompt to get a brief summary of the slide
	return f"""
Summarize the following slide content in one or two sentences:

{slide_content}

If you need clarification about the content, respond with exactly "CONTENT_CLARIFICATION_NEEDED" and nothing else.

Even if some aspects seem unclear, please provide your best attempt at a concise summary focusing on the main points you can confidently identify.
"""

def run_prompt_through_anthropic(input_text, output_file, temperature=0.7, max_retries=1):
	# Write prompt to input.txt
	with open(output_file.parent / 'input.txt', 'w', encoding='utf-8') as f:
		f.write(input_text.strip())

	# Call the anthropic processor
	cmd = ["python", "anthropic_file_processor.py",
		   "-i", str(output_file.parent / 'input.txt'),
		   "-o", str(output_file),
		   "-t", str(temperature)]

	for attempt in range(max_retries):
		try:
			result = subprocess.run(cmd, check=True, capture_output=True, text=True)

			# Read the output
			with open(output_file, 'r', encoding='utf-8') as f:
				response = f.read().strip()
				if response in ["TOPIC_CLARIFICATION_NEEDED", "CONTENT_CLARIFICATION_NEEDED"]:
					print(f"Warning: Language model needs clarification (attempt {attempt + 1}/{max_retries})")
					if attempt == max_retries - 1:
						print("Proceeding with best effort response...")
						return None
					continue
				return response

		except subprocess.CalledProcessError as e:
			print(f"Warning: anthropic_file_processor.py failed (attempt {attempt + 1}/{max_retries})")
			print(f"Error output: {e.stderr}")
			if attempt == max_retries - 1:
				print("Proceeding with best effort response...")
				return None
			continue

	return None

def insert_into_template(course_title, slide_title, slide_content, footer_notes=""):
	template = """<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>{{SLIDE_TITLE}} - {{COURSE_TITLE}}</title>
	<style>
		:root {
			--main-font: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
		}
		body {
			font-family: var(--main-font);
			margin: 0;
			padding: 0;
			min-height: 100vh;
			display: flex;
			flex-direction: column;
		}
		main {
			flex: 1;
			padding: 2rem;
			max-width: 1200px;
			margin: 0 auto;
			width: 100%;
			box-sizing: border-box;
		}
		h1, h2 {
			color: #1a1a1a;
			line-height: 1.2;
		}
		h1 {
			font-size: 2.5rem;
			margin-bottom: 1.5rem;
		}
		h2 {
			font-size: 2rem;
			margin: 1rem 0;
		}
		p, li {
			font-size: 1.5rem;
			line-height: 1.5;
			color: #333;
		}
		ul {
			padding-left: 2rem;
			margin: 1rem 0;
		}
		li {
			margin: 0.75rem 0;
			padding-left: 0.5rem;
		}
		.header {
			background: #333;
			color: white;
			padding: 1rem 2rem;
			font-size: 1.25rem;
		}
		.footer {
			background: #f5f5f5;
			padding: 1rem 2rem;
			font-size: 1rem;
			border-top: 1px solid #ddd;
		}
		.slide-number {
			position: absolute;
			top: 1rem;
			right: 1rem;
			font-size: 1.25rem;
			color: #666;
		}
	</style>
</head>
<body>
	<div class="header">{{COURSE_TITLE}}</div>
	<main>
		{{SLIDE_CONTENT}}
	</main>
	<div class="footer">{{FOOTER_NOTES}}</div>
</body>
</html>"""

	filled = template.replace("{{COURSE_TITLE}}", course_title)
	filled = filled.replace("{{SLIDE_TITLE}}", slide_title)
	filled = filled.replace("{{SLIDE_CONTENT}}", slide_content)
	filled = filled.replace("{{FOOTER_NOTES}}", footer_notes)
	return filled

def main():
	parser = argparse.ArgumentParser(description='Generate slides from course config')
	parser.add_argument('--output-dir', '-o', type=str, help='Output directory for slides')
	parser.add_argument('--test', action='store_true', help='Test mode - only generate first 5 slides')

	args = parser.parse_args()
	output_dir = args.output_dir

	if output_dir:
		output_dir = Path(output_dir)

	course_title, topics = parse_config("course_config.txt")

	if output_dir is None:
		# Create shorter directory name from first few words of course title
		words = course_title.lower().split()[:3]  # Take first 3 words
		dir_name = '_'.join(words).replace(":", "").replace("-", "_")
		slides_dir = Path(dir_name)

		# Ensure we don't clobber existing directory
		counter = 1
		original_dir = slides_dir
		while slides_dir.exists():
			slides_dir = Path(f"{original_dir}_{counter}")
			counter += 1
	else:
		slides_dir = output_dir
		if slides_dir.exists():
			print(f"Error: Output directory {slides_dir} already exists")
			sys.exit(1)

	slides_dir.mkdir(exist_ok=True)

	# Ensure summary_stack.txt exists in the slides directory
	summary_stack_path = slides_dir / "summary_stack.txt"
	if not summary_stack_path.exists():
		summary_stack_path.touch()

	slide_counter = 1
	for topic_num, topic in enumerate(topics, start=1):
		# Check if we've hit the test mode limit
		if args.test and slide_counter > 5:
			print("Test mode: Stopping after 5 slides")
			break

		# Read summary stack
		with open(summary_stack_path, 'r', encoding='utf-8') as f:
			summary_stack = f.read().strip()

		# Generate slide prompt
		prompt = generate_slide_prompt(course_title, summary_stack, topic)

		# Get slide content
		slide_content = run_prompt_through_anthropic(prompt, slides_dir / "slide_content.html")
		if slide_content is None:
			print(f"Warning: Skipping topic {topic_num} due to content generation failure")
			continue

		# Split content if needed
		slide_parts = slide_content.split("<!--SPLIT_SLIDE_HERE-->")

		for part_num, part_content in enumerate(slide_parts, start=1):
			# Check test mode limit again in case of split slides
			if args.test and slide_counter > 5:
				break

			# Insert into template
			slide_html = insert_into_template(course_title, f"Slide {slide_counter}", part_content.strip(), "")
			slide_filename = slides_dir / f"slide_{slide_counter:02d}.html"
			with open(slide_filename, 'w', encoding='utf-8') as f:
				f.write(slide_html)
			print(f"Created {slide_filename}")

			# Summarize this slide part and append to summary_stack
			summary_prompt = summarize_slide_prompt(part_content)
			slide_summary = run_prompt_through_anthropic(summary_prompt, slides_dir / "slide_summary.txt")
			if slide_summary is None:
				print(f"Warning: Failed to generate summary for slide {slide_counter}")
				continue

			# Append summary to summary_stack.txt
			with open(summary_stack_path, 'a', encoding='utf-8') as f:
				f.write(f"{slide_counter}. {slide_summary}\n")

			slide_counter += 1

if __name__ == "__main__":
	main()
# end generate_slides.py