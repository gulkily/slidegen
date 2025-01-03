# begin anthropic_file_processor.py

import anthropic
import os
import argparse
import sys
from pathlib import Path
import json

# Constants for Claude 3 Sonnet pricing (per 1K tokens)
INPUT_PRICE_PER_1K = 0.008  # $0.008 per 1K input tokens
OUTPUT_PRICE_PER_1K = 0.024  # $0.024 per 1K output tokens

class TokenTracker:
	def __init__(self):
		self.total_input_tokens = 0
		self.total_output_tokens = 0
		self.total_cost = 0.0

	def add_usage(self, input_tokens: int, output_tokens: int):
		"""Add token usage from a single API call"""
		self.total_input_tokens += input_tokens
		self.total_output_tokens += output_tokens
		input_cost, output_cost, total_cost = calculate_cost(input_tokens, output_tokens)
		self.total_cost += total_cost

	def get_stats(self):
		"""Get usage statistics as a dictionary"""
		return {
			"input_tokens": self.total_input_tokens,
			"output_tokens": self.total_output_tokens,
			"total_tokens": self.total_input_tokens + self.total_output_tokens,
			"total_cost": self.total_cost
		}

	def print_totals(self):
		"""Print cumulative token usage and costs"""
		print("\nTotal Run Statistics:")
		print(f"Total input tokens:  {self.total_input_tokens:,}")
		print(f"Total output tokens: {self.total_output_tokens:,}")
		print(f"Total tokens:        {self.total_input_tokens + self.total_output_tokens:,}")
		print(f"Total cost:          ${self.total_cost:.4f}")

def calculate_cost(input_tokens: int, output_tokens: int) -> tuple[float, float, float]:
	"""
	Calculate the cost of API usage based on input and output tokens.

	Args:
		input_tokens (int): Number of input tokens
		output_tokens (int): Number of output tokens

	Returns:
		tuple[float, float, float]: (input_cost, output_cost, total_cost) in USD
	"""
	input_cost = (input_tokens / 1000) * INPUT_PRICE_PER_1K
	output_cost = (output_tokens / 1000) * OUTPUT_PRICE_PER_1K
	total_cost = input_cost + output_cost
	return input_cost, output_cost, total_cost

def process_file(input_file: str, output_file: str, api_key: str, temperature: float, tracker: TokenTracker) -> bool:
	"""
	Read content from input file, query Anthropic API, and write response to output file

	Args:
		input_file (str): Path to input text file
		output_file (str): Path to output text file
		api_key (str): Anthropic API key
		temperature (float): Temperature setting for response randomness (0.0 to 1.0)
		tracker (TokenTracker): Token usage tracker instance

	Returns:
		bool: True if successful, False if an error occurred
	"""
	try:
		# Initialize the Anthropic client
		client = anthropic.Client(api_key=api_key)
	except Exception as e:
		print(f"Error initializing Anthropic client: {e}")
		return False

	# Read input file
	try:
		with open(input_file, 'r', encoding='utf-8') as f:
			content = f.read().strip()
	except FileNotFoundError:
		print(f"Error: Input file '{input_file}' not found.")
		return False
	except Exception as e:
		print(f"Error reading input file: {e}")
		return False

	if not content:
		print("Error: Input file is empty")
		return False

	# Send request to Anthropic API
	try:
		message = client.messages.create(
			model="claude-3-sonnet-20240229",
			max_tokens=1024,
			temperature=temperature,
			messages=[
				{
					"role": "user",
					"content": content
				}
			]
		)

		response = message.content[0].text

		# Get token usage and update tracker
		input_tokens = message.usage.input_tokens
		output_tokens = message.usage.output_tokens
		tracker.add_usage(input_tokens, output_tokens)

		# Calculate costs for this query
		input_cost, output_cost, total_cost = calculate_cost(input_tokens, output_tokens)

		# Print token usage and cost information for this query
		print(f"\nQuery Token Usage:")
		print(f"Input tokens:  {input_tokens:,}")
		print(f"Output tokens: {output_tokens:,}")
		print(f"Total tokens:  {input_tokens + output_tokens:,}")
		print(f"\nQuery Cost Breakdown:")
		print(f"Input cost:  ${input_cost:.4f}")
		print(f"Output cost: ${output_cost:.4f}")
		print(f"Total cost:  ${total_cost:.4f}")

	except Exception as e:
		print(f"Error calling Anthropic API: {str(e)}")
		return False

	# Write response to output file
	try:
		with open(output_file, 'w', encoding='utf-8') as f:
			f.write(response)
		return True
	except Exception as e:
		print(f"Error writing to output file: {e}")
		return False

def main():
	# Set up argument parser
	parser = argparse.ArgumentParser(
		description='Process text file through Anthropic API',
		formatter_class=argparse.ArgumentDefaultsHelpFormatter
	)

	parser.add_argument(
		'-i', '--input',
		default='input.txt',
		help='Path to input text file'
	)

	parser.add_argument(
		'-o', '--output',
		default='output.txt',
		help='Path to output text file'
	)

	parser.add_argument(
		'-t', '--temperature',
		type=float,
		default=0.7,
		help='Temperature setting (0.0 to 1.0) - lower values are more deterministic'
	)

	parser.add_argument(
		'--stats-file',
		help='Optional JSON file to write usage statistics to'
	)

	args = parser.parse_args()

	# Validate temperature
	if not 0.0 <= args.temperature <= 1.0:
		print("Error: Temperature must be between 0.0 and 1.0")
		sys.exit(1)

	# Get API key from environment variable
	api_key = os.getenv('ANTHROPIC_API_KEY')
	if not api_key:
		print("Error: ANTHROPIC_API_KEY environment variable not set")
		sys.exit(1)

	# Initialize token tracker
	tracker = TokenTracker()

	# Process the file
	success = process_file(args.input, args.output, api_key, args.temperature, tracker)

	# Print total usage statistics
	tracker.print_totals()

	# Write stats to file if requested
	if args.stats_file:
		stats = tracker.get_stats()
		with open(args.stats_file, 'w') as f:
			json.dump(stats, f)

	if not success:
		sys.exit(1)

if __name__ == "__main__":
	main()

# end anthropic_file_processor.py