#!/usr/bin/env python3
"""
InvoiceGenius AI Startup Script
===============================

This script provides an easy way to start the InvoiceGenius AI application
with proper environment setup and validation.

Usage:
    python start.py           # Start with default settings
    python start.py --setup   # Run initial setup wizard
    python start.py --check   # Check system requirements
    python start.py --reset   # Reset application to defaults
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse
import logging

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    """Print the InvoiceGenius AI banner"""
    banner = f"""
{Colors.HEADER}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                      🤖 InvoiceGenius AI                         ║
║            Intelligent Invoice Processing & Analytics            ║
║                                                                  ║
║            Transform your invoice workflow today!                ║
╚══════════════════════════════════════════════════════════════════╝
{Colors.ENDC}
"""
    print(banner)

def check_python_version():
    """Check if Python version is compatible"""
    min_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        print(f"{Colors.FAIL}❌ Python {min_version[0]}.{min_version[1]}+ required. "
              f"Current version: {current_version[0]}.{current_version[1]}{Colors.ENDC}")
        return False
    
    print(f"{Colors.OKGREEN}✅ Python version: {current_version[0]}.{current_version[1]} (compatible){Colors.ENDC}")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'streamlit', 'google-generativeai', 'pandas', 'numpy', 
        'pillow', 'openpyxl', 'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"{Colors.OKGREEN}✅ {package}{Colors.ENDC}")
        except ImportError:
            missing_packages.append(package)
            print(f"{Colors.FAIL}❌ {package} (missing){Colors.ENDC}")
    
    if missing_packages:
        print(f"\n{Colors.WARNING}📦 Installing missing packages...{Colors.ENDC}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '--upgrade'
            ] + missing_packages)
            print(f"{Colors.OKGREEN}✅ All packages installed successfully!{Colors.ENDC}")
            return True
        except subprocess.CalledProcessError:
            print(f"{Colors.FAIL}❌ Failed to install packages. Please run: pip install -r requirements.txt{Colors.ENDC}")
            return False
    
    return True

def check_environment():
    """Check if environment is properly configured"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print(f"{Colors.WARNING}⚠️  .env file not found{Colors.ENDC}")
        return False
    
    # Check if GOOGLE_API_KEY is set
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key or api_key == 'your_google_ai_api_key_here':
        print(f"{Colors.WARNING}⚠️  GOOGLE_API_KEY not configured in .env file{Colors.ENDC}")
        return False
    
    print(f"{Colors.OKGREEN}✅ Environment configuration looks good{Colors.ENDC}")
    return True

def create_directories():
    """Create necessary directories"""
    directories = ['data', 'logs', 'exports', 'assets']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"{Colors.OKGREEN}✅ Created directory: {directory}{Colors.ENDC}")

def setup_wizard():
    """Interactive setup wizard for first-time users"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}🧙‍♂️ InvoiceGenius AI Setup Wizard{Colors.ENDC}")
    print("Let's get you up and running!\n")
    
    # Step 1: Copy environment template
    env_template = Path('.env.template')
    env_file = Path('.env')
    
    if env_template.exists() and not env_file.exists():
        shutil.copy(env_template, env_file)
        print(f"{Colors.OKGREEN}✅ Created .env file from template{Colors.ENDC}")
    
    # Step 2: Get Google AI API Key
    print(f"\n{Colors.OKCYAN}Step 1: Google AI API Key{Colors.ENDC}")
    print("You need a Google AI API key to use the AI processing features.")
    print("Get one free at: https://makersuite.google.com/app/apikey")
    
    api_key = input(f"\n{Colors.BOLD}Enter your Google AI API key: {Colors.ENDC}").strip()
    
    if api_key:
        # Update the .env file
        with open(env_file, 'r') as f:
            content = f.read()
        
        content = content.replace('your_google_ai_api_key_here', api_key)
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"{Colors.OKGREEN}✅ API key saved to .env file{Colors.ENDC}")
    
    # Step 3: Basic configuration
    print(f"\n{Colors.OKCYAN}Step 2: Basic Configuration{Colors.ENDC}")
    
    company_name = input(f"{Colors.BOLD}Company name (for reports): {Colors.ENDC}").strip()
    if company_name:
        with open(env_file, 'r') as f:
            content = f.read()
        content = content.replace('Your Company Name', company_name)
        with open(env_file, 'w') as f:
            f.write(content)
        print(f"{Colors.OKGREEN}✅ Company name updated{Colors.ENDC}")
    
    # Step 4: Create directories
    print(f"\n{Colors.OKCYAN}Step 3: Creating directories{Colors.ENDC}")
    create_directories()
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 Setup complete! You're ready to start processing invoices.{Colors.ENDC}")
    print(f"\n{Colors.OKCYAN}Next steps:{Colors.ENDC}")
    print("1. Run: python start.py")
    print("2. Open your browser to the displayed URL")
    print("3. Upload an invoice and watch the magic happen!")

def check_system():
    """Check system requirements and configuration"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}🔍 System Check{Colors.ENDC}")
    
    checks_passed = 0
    total_checks = 4
    
    # Check Python version
    print(f"\n{Colors.OKCYAN}Checking Python version...{Colors.ENDC}")
    if check_python_version():
        checks_passed += 1
    
    # Check dependencies
    print(f"\n{Colors.OKCYAN}Checking dependencies...{Colors.ENDC}")
    if check_dependencies():
        checks_passed += 1
    
    # Check environment
    print(f"\n{Colors.OKCYAN}Checking environment configuration...{Colors.ENDC}")
    if check_environment():
        checks_passed += 1
    
    # Check directories
    print(f"\n{Colors.OKCYAN}Checking directories...{Colors.ENDC}")
    create_directories()
    checks_passed += 1
    
    # Summary
    print(f"\n{Colors.HEADER}{Colors.BOLD}📊 System Check Summary{Colors.ENDC}")
    if checks_passed == total_checks:
        print(f"{Colors.OKGREEN}✅ All checks passed! ({checks_passed}/{total_checks}){Colors.ENDC}")
        print(f"{Colors.OKGREEN}🚀 Ready to launch InvoiceGenius AI!{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.WARNING}⚠️  {checks_passed}/{total_checks} checks passed{Colors.ENDC}")
        print(f"{Colors.WARNING}Please resolve the issues above before starting the application.{Colors.ENDC}")
        return False

def reset_application():
    """Reset application to defaults"""
    print(f"\n{Colors.WARNING}{Colors.BOLD}🔄 Resetting InvoiceGenius AI{Colors.ENDC}")
    
    confirm = input(f"{Colors.WARNING}This will clear all data and logs. Continue? (y/N): {Colors.ENDC}").strip().lower()
    
    if confirm == 'y':
        # Clear data directory
        data_dir = Path('data')
        if data_dir.exists():
            shutil.rmtree(data_dir)
            print(f"{Colors.OKGREEN}✅ Cleared data directory{Colors.ENDC}")
        
        # Clear logs directory
        logs_dir = Path('logs')
        if logs_dir.exists():
            shutil.rmtree(logs_dir)
            print(f"{Colors.OKGREEN}✅ Cleared logs directory{Colors.ENDC}")
        
        # Clear exports directory
        exports_dir = Path('exports')
        if exports_dir.exists():
            shutil.rmtree(exports_dir)
            print(f"{Colors.OKGREEN}✅ Cleared exports directory{Colors.ENDC}")
        
        # Recreate directories
        create_directories()
        
        print(f"{Colors.OKGREEN}🎉 Application reset complete!{Colors.ENDC}")
    else:
        print(f"{Colors.OKCYAN}Reset cancelled.{Colors.ENDC}")

def start_application():
    """Start the Streamlit application"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}🚀 Starting InvoiceGenius AI...{Colors.ENDC}")
    
    # Quick system check
    if not check_environment():
        print(f"{Colors.FAIL}❌ Environment not properly configured. Run: python start.py --setup{Colors.ENDC}")
        return False
    
    print(f"{Colors.OKCYAN}🌟 Launching web interface...{Colors.ENDC}")
    print(f"{Colors.OKCYAN}📱 The application will open in your browser automatically.{Colors.ENDC}")
    print(f"{Colors.OKCYAN}🛑 Press Ctrl+C to stop the application.{Colors.ENDC}\n")
    
    try:
        # Start Streamlit
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--theme.base', 'light',
            '--theme.primaryColor', '#366092',
            '--theme.backgroundColor', '#ffffff',
            '--theme.secondaryBackgroundColor', '#f0f2f6'
        ])
    except KeyboardInterrupt:
        print(f"\n{Colors.OKCYAN}👋 Thanks for using InvoiceGenius AI!{Colors.ENDC}")
    except FileNotFoundError:
        print(f"{Colors.FAIL}❌ Streamlit not found. Please install requirements: pip install -r requirements.txt{Colors.ENDC}")
        return False
    
    return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='InvoiceGenius AI Startup Script')
    parser.add_argument('--setup', action='store_true', help='Run setup wizard')
    parser.add_argument('--check', action='store_true', help='Check system requirements')
    parser.add_argument('--reset', action='store_true', help='Reset application to defaults')
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.setup:
        setup_wizard()
    elif args.check:
        if check_system():
            print(f"\n{Colors.OKGREEN}Ready to start with: python start.py{Colors.ENDC}")
    elif args.reset:
        reset_application()
    else:
        start_application()

if __name__ == '__main__':
    main()