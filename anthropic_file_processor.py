# begin anthropic_file_processor.py

import anthropic
import os
import argparse
import sys
from pathlib import Path

def process_file(input_file: str, output_file: str, api_key: str, temperature: float) -> bool:
    """
    Read content from input file, query Anthropic API, and write response to output file
    
    Args:
        input_file (str): Path to input text file
        output_file (str): Path to output text file
        api_key (str): Anthropic API key
        temperature (float): Temperature setting for response randomness (0.0 to 1.0)
        
    Returns:
        bool: True if successful, False if an error occurred
    """
    # Initialize the Anthropic client
    client = anthropic.Client(api_key=api_key)
    
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

    # Send request to Anthropic API
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
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
        
    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        return False

    # Write response to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response)
        print(f"Response successfully written to {output_file}")
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

    # Process the file with provided arguments
    success = process_file(args.input, args.output, api_key, args.temperature)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

# end anthropic_file_processor.py