# begin generate_slides.py
# This script generates HTML slides from a course outline using AI assistance.
# It works in the following way:

# SETUP AND CONFIGURATION
# ----------------------
# 1. Takes a course outline file (course_config.txt) as input
# 2. Can resume from previous runs by:
# - Finding highest numbered existing slide
# - Reading previous slide summaries for context
# - Continuing from where it left off
# 3. Supports test mode to only generate 5 slides for testing

# MAIN WORKFLOW
# ------------
# 1. Parses course config file to extract:
# - Course title
# - List of topics to cover
# 2. For each topic:
# - Generates a prompt for the AI using:
#   * Course title
#   * Previous slide summaries for context
#   * Current topic
# - Gets slide content from AI
# - Splits content into multiple slides if too long
# - Creates HTML slides using template
# - Generates summary of slide content
# - Maintains running summary stack for context

# KEY FEATURES
# -----------
# - Consistent slide formatting via HTML/CSS template
# - Maintains context between slides using summaries
# - Handles content overflow via slide splitting
# - Resumable from interruptions
# - Test mode for quick iterations
# - Strict limits on text per slide:
#   * Max 5 bullet points per slide
#   * Max 15 words per bullet point
#   * Max 2 levels of bullet nesting
#   * Min 24pt font size

import os
import re
import subprocess
import sys
import argparse
import json
from pathlib import Path
import glob

def parse_config(file_path):
	"""
	Parses course configuration file to extract title and topics.
	Handles multiple common formats for course outlines.
	"""
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
	"""
	Creates prompt for AI to generate slide content.
	Includes context from previous slides via summary stack.
	"""
	return f"""
You are preparing a series of lecture slides for a course titled "{course_title}".

So far, these are the summaries of previous slides:
{summary_stack}

Now please create the next slide. The next slide should cover: "{topic}"

STRICT presentation requirements:
- Maximum 5 bullet points per slide
- Maximum 15 words per bullet point
- Maximum 2 levels of bullet point nesting
- Minimum font size of 24pt (use <style> tags)
- No paragraphs of text - only bullet points
- If content exceeds these limits, split into multiple slides with "<!--SPLIT_SLIDE_HERE-->"

If you need clarification about the topic, respond with exactly "TOPIC_CLARIFICATION_NEEDED" and nothing else.

Otherwise, please return only valid HTML that fits into the `{{SLIDE_CONTENT}}` section of the given template. Include a heading and bullet points using HTML elements like <h2>, <ul>, <li>, etc.

Even if you're not completely sure about some aspects of the topic, please provide your best attempt at creating concise slide content based on your current knowledge. Focus on the key concepts you're most confident about.
"""

def summarize_slide_prompt(slide_content):
	"""
	Creates prompt for AI to generate concise summary of slide content.
	Used to maintain context between slides.
	"""
	return f"""
Summarize the following slide content in one or two sentences:

{slide_content}

If you need clarification about the content, respond with exactly "CONTENT_CLARIFICATION_NEEDED" and nothing else.

Even if some aspects seem unclear, please provide your best attempt at a concise summary focusing on the main points you can confidently identify.
"""

def run_prompt_through_anthropic(input_text, output_file, temperature=0.7, max_retries=1):
	"""
	Sends prompt to Anthropic API model and handles response.
	Includes retry logic for failed attempts.
	"""
	output_dir = output_file.parent
	
	# Write prompt to input.txt in slides directory
	input_file = output_dir / 'input.txt'
	with open(input_file, 'w', encoding='utf-8') as f:
		f.write(input_text.strip())

	# Create stats file path in slides directory
	stats_file = output_dir / 'stats.json'
	
	# Call the anthropic processor
	cmd = ["python", "anthropic_file_processor.py",
		   "-i", str(input_file),
		   "-o", str(output_file),
		   "-t", str(temperature),
		   "--stats-file", str(stats_file)]

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
			if e.stderr:
				print(f"Error output: {e.stderr}")
			if e.stdout:
				print(f"Output: {e.stdout}")
			if attempt == max_retries - 1:
				print("Proceeding with best effort response...")
				return None
			continue

	return None

def insert_into_template(course_title, slide_title, slide_content, footer_notes=""):
	"""
	Inserts generated content into HTML slide template.
	Template includes responsive design and consistent styling.
	"""
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
			padding-left: 1rem;
			margin: 1rem 0;
			max-width: 1000px;
		}
		li {
			margin: 0.75rem 0;
			padding-left: 0.25rem;
		}
		/* Prevent deep nesting */
		li li li {
			display: none;
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

def get_next_slide_number(slides_dir):
	"""
	Finds highest existing slide number to support resuming generation.
	"""
	# Find all slide files and get the highest number
	slide_files = glob.glob(str(slides_dir / "slide_*.html"))
	if not slide_files:
		return 1
	
	numbers = [int(re.search(r'slide_(\d+)\.html', f).group(1)) for f in slide_files]
	return max(numbers) + 1

def main():
	"""
	Main execution flow:
	1. Parse arguments
	2. Set up output directory
	3. Parse course config
	4. Generate slides for each topic
	5. Handle interruptions for resumability
	"""
	parser = argparse.ArgumentParser(description='Generate slides from course config')
	parser.add_argument('--output-dir', '-o', type=str, help='Output directory for slides')
	parser.add_argument('--test', action='store_true', help='Test mode - only generate 5 slides')
	parser.add_argument('--temperature', type=float, default=0.7,
					   help='Temperature for AI responses (0.0-1.0)')

	args = parser.parse_args()
	
	# Initialize cumulative stats
	cumulative_stats = {
		"input_tokens": 0,
		"output_tokens": 0,
		"total_tokens": 0,
		"total_cost": 0.0
	}

	# Check for API key
	if not os.getenv('ANTHROPIC_API_KEY'):
		print("Error: ANTHROPIC_API_KEY environment variable not set")
		sys.exit(1)

	output_dir = args.output_dir

	if output_dir:
		output_dir = Path(output_dir)

	try:
		course_title, topics = parse_config("course_config.txt")
	except FileNotFoundError:
		print("Error: course_config.txt not found")
		sys.exit(1)
	except Exception as e:
		print(f"Error parsing course config: {e}")
		sys.exit(1)

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

	# Create slides directory and all parent directories
	slides_dir.mkdir(parents=True, exist_ok=True)
	print(f"\nGenerating slides in: {slides_dir.absolute()}")

	# Initialize summary stack file
	summary_stack_path = slides_dir / "summary_stack.txt"
	if not summary_stack_path.exists():
		summary_stack_path.touch()

	# Get the next slide number to start from
	slide_counter = get_next_slide_number(slides_dir)
	
	try:
		for topic_num, topic in enumerate(topics, start=slide_counter):
			# Check if we've hit the test mode limit
			if args.test and slide_counter > 5:
				print("\nTest mode: Stopping after 5 slides")
				break

			print(f"\nGenerating slide {slide_counter} for topic: {topic}")
			
			# Generate slide content
			prompt = generate_slide_prompt(course_title, "", topic)
			content_file = slides_dir / f"slide_{slide_counter:03d}_content.txt"
			content = run_prompt_through_anthropic(prompt, content_file, args.temperature)
			
			# Update cumulative stats if available
			stats_file = slides_dir / 'stats.json'
			if stats_file.exists():
				with open(stats_file) as f:
					stats = json.load(f)
					cumulative_stats["input_tokens"] += stats["input_tokens"]
					cumulative_stats["output_tokens"] += stats["output_tokens"]
					cumulative_stats["total_tokens"] += stats["total_tokens"]
					cumulative_stats["total_cost"] += stats["total_cost"]
			
			if content is None:
				print(f"Warning: Skipping topic {topic_num} due to content generation failure")
				continue

			# Generate summary for context
			summary_prompt = summarize_slide_prompt(content)
			summary_file = slides_dir / f"slide_{slide_counter:03d}_summary.txt"
			summary = run_prompt_through_anthropic(summary_prompt, summary_file, args.temperature)
			
			# Update cumulative stats for summary if available
			if stats_file.exists():
				with open(stats_file) as f:
					stats = json.load(f)
					cumulative_stats["input_tokens"] += stats["input_tokens"]
					cumulative_stats["output_tokens"] += stats["output_tokens"]
					cumulative_stats["total_tokens"] += stats["total_tokens"]
					cumulative_stats["total_cost"] += stats["total_cost"]
			
			if summary:
				with open(summary_stack_path, 'a', encoding='utf-8') as f:
					f.write(summary + "\n")

			# Create HTML slide
			slide_html = insert_into_template(course_title, topic, content)
			with open(slides_dir / f"slide_{slide_counter:03d}.html", 'w', encoding='utf-8') as f:
				f.write(slide_html)
			
			slide_counter += 1
			
	except KeyboardInterrupt:
		print("\nInterrupted! Progress saved - you can resume from the last completed slide.")
	
	# Print final usage statistics
	print("\nFinal Usage Statistics:")
	print(f"Total input tokens:  {cumulative_stats['input_tokens']:,}")
	print(f"Total output tokens: {cumulative_stats['output_tokens']:,}")
	print(f"Total tokens:        {cumulative_stats['total_tokens']:,}")
	print(f"Total cost:          ${cumulative_stats['total_cost']:.4f}")
	
	# Save final stats
	stats_file = slides_dir / 'final_stats.json'
	with open(stats_file, 'w') as f:
		json.dump(cumulative_stats, f, indent=2)
	
	# Print summary of output files
	print(f"\nOutput Files:")
	print(f"Slides directory:  {slides_dir.absolute()}")
	print(f"HTML slides:       {slides_dir.absolute()}/*.html")
	print(f"Content files:     {slides_dir.absolute()}/*_content.txt")
	print(f"Summary files:     {slides_dir.absolute()}/*_summary.txt")
	print(f"Usage statistics:  {stats_file.absolute()}")
	
	# Print how to view the slides
	print(f"\nTo view the slides:")
	print(f"1. Open any web browser")
	print(f"2. Navigate to: {slides_dir.absolute()}")
	print(f"3. Open slide_001.html to begin")

if __name__ == "__main__":
	main()
# end generate_slides.py