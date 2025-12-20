import os
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

# Get the directory where this file is located
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(os.path.dirname(CURRENT_DIR), 'email_templates')

# Initialize Jinja2 environment
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def render_email_template(template_name, context):
    """
    Render an email template with the given context variables.
    
    Args:
        template_name (str): Name of the template file (e.g., 'welcome.html')
        context (dict): Dictionary of variables to render in the template
        
    Returns:
        str: Rendered HTML content
        
    Raises:
        TemplateNotFound: If template file doesn't exist
    """
    try:
        template = jinja_env.get_template(template_name)
        return template.render(context)
    except TemplateNotFound:
        raise TemplateNotFound(f"Email template '{template_name}' not found in {TEMPLATES_DIR}")
    except Exception as e:
        raise Exception(f"Error rendering template '{template_name}': {str(e)}")


def get_template_path(template_name):
    """Get the full path to a template file."""
    return os.path.join(TEMPLATES_DIR, template_name)


def template_exists(template_name):
    """Check if a template file exists."""
    return os.path.exists(get_template_path(template_name))
