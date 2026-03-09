FROM e2bdev/code-interpreter:latest

# Pre-install all packages required by Finch skills.
# Add new packages here whenever a skill declares a new `bins` dependency.
# After editing, rebuild the template: cd backend/sandbox && python build_template.py
RUN pip install --no-cache-dir \
    cryptography
