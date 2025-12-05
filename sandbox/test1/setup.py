# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

import os
import json
from pathlib import Path

def setup_autogen_files():
    """Create the AutoGen Studio structure directly"""
    
    # Create directory structure
    base_dir = Path.home() / '.autogenstudio'
    base_dir.mkdir(exist_ok=True)
    
    skills_dir = base_dir / 'skills'
    skills_dir.mkdir(exist_ok=True)
    
    # Load the configuration
    with open('redteam-agents.json', 'r') as f:
        config = json.load(f)
    
    # Save each skill as a Python file
    for skill in config['skills']:
        skill_file = skills_dir / f"{skill['name']}.py"
        with open(skill_file, 'w') as f:
            f.write(skill['content'])
        print(f"Created skill: {skill['name']}")
    
    # Create agents configuration
    agents_config = base_dir / 'agents.json'
    with open(agents_config, 'w') as f:
        json.dump(config['agents'], f, indent=2)
    print(f"Created agents config")
    
    # Create workflows configuration
    workflows_config = base_dir / 'workflows.json'
    with open(workflows_config, 'w') as f:
        json.dump(config['workflows'], f, indent=2)
    print(f"Created workflows config")
    
    print("\n✅ Setup complete! Now start AutoGen Studio:")
    print("   autogenstudio ui --port 8080")

if __name__ == "__main__":
    setup_autogen_files()
