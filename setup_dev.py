"""Development environment setup script."""

import os
import sys
import subprocess
import venv
from pathlib import Path


def create_venv():
    """Create virtual environment."""
    venv_path = Path("venv")
    if venv_path.exists():
        print("Virtual environment already exists.")
        return venv_path
    
    print("Creating virtual environment...")
    venv.create(venv_path, with_pip=True)
    return venv_path


def install_dependencies(venv_path):
    """Install project dependencies."""
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip"
        python_path = venv_path / "Scripts" / "python"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    print("Installing dependencies...")
    subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
    subprocess.run([str(pip_path), "install", "pytest", "pytest-asyncio"], check=True)
    
    return python_path


def create_env_template():
    """Create .env template file."""
    env_template = """# WhatsApp GPT Assistant Configuration

OPENAI_API_KEY=your_openai_api_key_here

TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

GOOGLE_CREDENTIALS_PATH=path/to/your/google/credentials.json
GOOGLE_TOKEN_PATH=path/to/your/google/token.json

TIMEZONE=Asia/Jerusalem
DEBUG_LOG_PROMPTS=false
LOG_LEVEL=INFO
CONFIRM_TTL_MIN=10

OPENAI_RATE_LIMIT_RPM=60
OPENAI_RATE_LIMIT_TPM=40000

DAILY_DIGEST_HOUR=7
DAILY_DIGEST_MINUTE=0
"""
    
    env_file = Path(".env.template")
    if not env_file.exists():
        print("Creating .env template...")
        env_file.write_text(env_template)
        print("Created .env.template - copy this to .env and fill in your values")


def create_pycharm_config():
    """Create PyCharm configuration files."""
    idea_dir = Path(".idea")
    idea_dir.mkdir(exist_ok=True)
    
    run_config = """<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="WhatsApp Assistant" type="PythonConfigurationType" factoryName="Python">
    <module name="whatsapp-gpt-assistant" />
    <option name="INTERPRETER_OPTIONS" value="" />
    <option name="PARENT_ENVS" value="true" />
    <envs>
      <env name="PYTHONUNBUFFERED" value="1" />
    </envs>
    <option name="SDK_HOME" value="$PROJECT_DIR$/venv/bin/python" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$" />
    <option name="IS_MODULE_SDK" value="false" />
    <option name="ADD_CONTENT_ROOTS" value="true" />
    <option name="ADD_SOURCE_ROOTS" value="true" />
    <option name="SCRIPT_NAME" value="-m" />
    <option name="PARAMETERS" value="uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" />
    <option name="SHOW_COMMAND_LINE" value="false" />
    <option name="EMULATE_TERMINAL" value="false" />
    <option name="MODULE_MODE" value="true" />
    <option name="REDIRECT_INPUT" value="false" />
    <option name="INPUT_FILE" value="" />
    <method v="2" />
  </configuration>
</component>"""
    
    (idea_dir / "runConfigurations").mkdir(exist_ok=True)
    (idea_dir / "runConfigurations" / "WhatsApp_Assistant.xml").write_text(run_config)
    
    test_config = """<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="Tests" type="tests" factoryName="py.test">
    <module name="whatsapp-gpt-assistant" />
    <option name="INTERPRETER_OPTIONS" value="" />
    <option name="PARENT_ENVS" value="true" />
    <option name="SDK_HOME" value="$PROJECT_DIR$/venv/bin/python" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$" />
    <option name="IS_MODULE_SDK" value="false" />
    <option name="ADD_CONTENT_ROOTS" value="true" />
    <option name="ADD_SOURCE_ROOTS" value="true" />
    <option name="_new_keywords" value="&quot;&quot;" />
    <option name="_new_parameters" value="&quot;&quot;" />
    <option name="_new_additionalArguments" value="&quot;&quot;" />
    <option name="_new_target" value="&quot;$PROJECT_DIR$/tests&quot;" />
    <option name="_new_targetType" value="&quot;PATH&quot;" />
    <method v="2" />
  </configuration>
</component>"""
    
    (idea_dir / "runConfigurations" / "Tests.xml").write_text(test_config)
    print("Created PyCharm run configurations")


def main():
    """Main setup function."""
    print("Setting up WhatsApp GPT Assistant development environment...")
    
    venv_path = create_venv()
    
    python_path = install_dependencies(venv_path)
    
    create_env_template()
    create_pycharm_config()
    
    print("\n" + "="*60)
    print("Development environment setup complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Copy .env.template to .env and fill in your API keys")
    print("2. Set up Google OAuth credentials")
    print("3. Configure Twilio webhook URL")
    print("\nTo run the application:")
    print(f"  {python_path} -m uvicorn app.main:app --reload")
    print("\nTo run tests:")
    print(f"  {python_path} -m pytest")
    print("\nFor PyCharm:")
    print("  - Open this directory as a project")
    print("  - Set interpreter to: venv/bin/python")
    print("  - Use the pre-configured run configurations")


if __name__ == "__main__":
    main()
