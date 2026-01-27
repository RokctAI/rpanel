import re

# Read the file
with open(r'rpanel\hosting\doctype\hosted_website\hosted_website.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the template - replace {self.xxx} with {xxx} and add .format()
pattern = r'(config_content = r""".*?""")'
def fix_template(match):
    template = match.group(1)
    # Replace {self.domain} with {domain}, etc.
    template = template.replace('{self.domain}', '{domain}')
    template = template.replace('{self.site_path}', '{site_path}')
    # Add .format() call
    template += '.format(listen_block=listen_block, domain=self.domain, site_path=self.site_path, ssl_block=ssl_block, php_socket=php_socket)'
    return template

content = re.sub(pattern, fix_template, content, flags=re.DOTALL)

#Write back
with open(r'rpanel\hosting\doctype\hosted_website\hosted_website.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed nginx config template")
