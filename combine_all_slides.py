# begin combine_all_slides.py
import glob
import os
import sys
from pathlib import Path
import re

# CSS styles template that will be moved to styles.css
CSS_TEMPLATE = """body { 
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    margin: 0;
    padding: 0;
    background: #f5f5f5;
}
nav { 
    background: #333; 
    color: #fff; 
    padding: 1rem 2rem;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: center;
}
nav a { 
    color: #fff;
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    transition: background-color 0.2s;
}
nav a:hover {
    background-color: rgba(255, 255, 255, 0.1);
}
.slide { 
    min-height: calc(100vh - 4rem);
    padding: 3rem 2rem 2rem;
    margin: 0 auto;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    background: white;
    margin-bottom: 2px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    position: relative;
    max-width: 1200px;
}
#slides-container {
    margin-top: 4rem;
    scroll-snap-type: y mandatory;
    overflow-y: auto;
    height: calc(100vh - 4rem);
}
.slide-title {
    position: absolute;
    top: 1rem;
    right: 1rem;
    color: #666;
    font-size: 1.25rem;
}
h1, h2 {
    color: #1a1a1a;
    line-height: 1.2;
    margin-top: 0;
}
h1 { font-size: 2.5rem; }
h2 { font-size: 2rem; }
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
@media (max-width: 768px) {
    nav {
        padding: 0.75rem 1rem;
    }
    .slide {
        padding: 2rem 1rem 1rem;
    }
    h1 { font-size: 2rem; }
    h2 { font-size: 1.75rem; }
    p, li { font-size: 1.25rem; }
}"""

# JavaScript template that will be moved to script.js
JS_TEMPLATE = """document.addEventListener('DOMContentLoaded', function() {
    const slides = document.querySelectorAll('.slide');
    let currentSlide = 0;

    function goToSlide(index) {
        if (index >= 0 && index < slides.length) {
            currentSlide = index;
            slides[index].scrollIntoView({ behavior: 'smooth' });
            updateHash(index);
        }
    }

    function updateHash(index) {
        history.replaceState(null, null, `#slide_${index + 1}`);
    }

    // Initialize to hash location or first slide
    const hash = window.location.hash;
    if (hash) {
        const slideNum = parseInt(hash.split('_')[1]) - 1;
        if (!isNaN(slideNum) && slideNum >= 0 && slideNum < slides.length) {
            currentSlide = slideNum;
            slides[currentSlide].scrollIntoView();
        }
    }

    document.addEventListener('keydown', function(e) {
        switch(e.key) {
            case 'ArrowLeft':
            case 'ArrowUp':
                e.preventDefault();
                goToSlide(currentSlide - 1);
                break;
            case 'ArrowRight':
            case 'ArrowDown':
            case ' ':
                e.preventDefault();
                goToSlide(currentSlide + 1);
                break;
            case 'Home':
                e.preventDefault();
                goToSlide(0);
                break;
            case 'End':
                e.preventDefault();
                goToSlide(slides.length - 1);
                break;
        }
    });

    // Update current slide on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const newIndex = Array.from(slides).indexOf(entry.target);
                if (newIndex !== currentSlide) {
                    currentSlide = newIndex;
                    updateHash(currentSlide);
                }
            }
        });
    }, {threshold: 0.5});

    slides.forEach(slide => observer.observe(slide));
});"""

# HTML template that will be moved to template.html
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>All Slides</title>
    <link rel="stylesheet" href="styles.css">
    <script src="script.js"></script>
</head>
<body>
    <nav>
        <strong>Course Slides</strong>
        {nav_section}
    </nav>
    <div id="slides-container">
        {slides_content}
    </div>
</body>
</html>"""

def get_updated_styles():
    # TODO: Once templates are created, replace this with:
    # with open('styles.css', 'r', encoding='utf-8') as f:
    #     return f.read()
    return CSS_TEMPLATE

def find_slides_dir(specified_dir=None):
    if specified_dir:
        slides_dir = Path(specified_dir)
        if slides_dir.exists() and any(slides_dir.glob("slide_*.html")):
            return slides_dir
        print(f"Error: No slides found in {specified_dir}")
        sys.exit(1)

    # Look for directories containing slides
    potential_dirs = []
    for dir_path in Path('.').iterdir():
        if dir_path.is_dir() and any(dir_path.glob("slide_*.html")):
            potential_dirs.append(dir_path)

    if not potential_dirs:
        print("Error: No directories containing slides found")
        sys.exit(1)

    if len(potential_dirs) == 1:
        dir_path = potential_dirs[0]
        response = input(f"Found slides in directory '{dir_path}'. Use this directory? [Y/n] ")
        if response.lower() in ['', 'y', 'yes']:
            return dir_path
        sys.exit(0)

    print("Multiple directories with slides found:")
    for i, dir_path in enumerate(potential_dirs, 1):
        print(f"{i}. {dir_path}")
    print("Please specify directory using command line argument")
    sys.exit(1)

def extract_slide_content(slide_path):
    with open(slide_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract just the slide content between main tags
    match = re.search(r'<main>(.*?)</main>', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def main():
    # Get slides directory
    slides_dir = find_slides_dir(sys.argv[1] if len(sys.argv) > 1 else None)

    # TODO: Create template files
    # with open(slides_dir / 'styles.css', 'w', encoding='utf-8') as f:
    #     f.write(CSS_TEMPLATE)
    # with open(slides_dir / 'script.js', 'w', encoding='utf-8') as f:
    #     f.write(JS_TEMPLATE)
    # with open(slides_dir / 'template.html', 'w', encoding='utf-8') as f:
    #     f.write(HTML_TEMPLATE)

    output_file = slides_dir / "combined_slides.html"
    # Use set to remove duplicates and sort to maintain order
    slides = sorted(set(slides_dir.glob("slide_*.html")))

    # Generate navigation links
    nav_links = []
    for i, slide in enumerate(slides, 1):
        slide_name = f"Slide {i}"
        nav_links.append(f'<a href="#slide_{i}">{slide_name}</a>')

    nav_section = " | ".join(nav_links)

    # Build slides content
    slides_content = ""
    for i, slide in enumerate(slides, 1):
        slide_id = f"slide_{i}"
        slide_content = extract_slide_content(slide)
        if slide_content:  # Only add slide if it has content
            slides_content += f"""        <div class="slide" id="{slide_id}">
            <div class="slide-title">Slide {i}</div>
            {slide_content}
        </div>\n\n"""

    # TODO: Once templates are created, replace this with:
    # with open(slides_dir / 'template.html', 'r', encoding='utf-8') as f:
    #     html_template = f.read()
    # html_content = html_template.format(
    #     nav_section=nav_section,
    #     slides_content=slides_content
    # )

    # For now, build the HTML content inline
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>All Slides</title>
    <style>{get_updated_styles()}</style>
    <script>{JS_TEMPLATE}</script>
</head>
<body>
    <nav>
        <strong>Course Slides</strong>
        {nav_section}
    </nav>
    <div id="slides-container">
{slides_content}    </div>
</body>
</html>"""

    # Write the combined file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Combined slides written to {output_file}")

if __name__ == "__main__":
    main()

# end combine_all_slides.py