import os
import re

def convert_html_to_jsx(html_content):
    # Very basic JSX conversion
    content = html_content
    content = content.replace('class="', 'className="')
    content = content.replace('for="', 'htmlFor="')
    content = content.replace('stroke-width="', 'strokeWidth="')
    content = content.replace('stroke-linecap="', 'strokeLinecap="')
    content = content.replace('stroke-linejoin="', 'strokeLinejoin="')
    content = content.replace('fill-rule="', 'fillRule="')
    content = content.replace('clip-rule="', 'clipRule="')
    content = content.replace('tabindex="', 'tabIndex="')
    content = content.replace('<!--', '{/*')
    content = content.replace('-->', '*/}')
    # Close img and input tags
    content = re.sub(r'(<img[^>]*?)(?<!/)>', r'\1 />', content)
    content = re.sub(r'(<input[^>]*?)(?<!/)>', r'\1 />', content)
    content = re.sub(r'(<hr[^>]*?)(?<!/)>', r'\1 />', content)
    content = re.sub(r'(<br[^>]*?)(?<!/)>', r'\1 />', content)
    return content

def extract_main_and_header(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Extract header
    header_match = re.search(r'(<header.*?</header>)', html, re.DOTALL)
    header = header_match.group(1) if header_match else ""
    
    # Extract main
    main_match = re.search(r'(<main.*?</main>)', html, re.DOTALL)
    main_content = main_match.group(1) if main_match else ""
    
    # Extract footer
    footer_match = re.search(r'(<footer.*?</footer>)', html, re.DOTALL)
    footer = footer_match.group(1) if footer_match else ""
    
    return convert_html_to_jsx(header), convert_html_to_jsx(main_content), convert_html_to_jsx(footer)

base_dir = r"C:\Users\MontaserAbdalla\Downloads\stitch_ (4)\stitch_"
screens = ["pix_desktop_1", "pix_desktop_2", "pix_desktop_3", "pix_desktop_4"]

for screen in screens:
    path = os.path.join(base_dir, screen, "code.html")
    if os.path.exists(path):
        header, main_content, footer = extract_main_and_header(path)
        with open(f"{screen}.tsx", "w", encoding="utf-8") as f:
            f.write(f"// HEADER\n{header}\n\n// MAIN\n{main_content}\n\n// FOOTER\n{footer}")
        print(f"Processed {screen}")
