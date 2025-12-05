# Copyright (c) 2025 adcl.io
# All Rights Reserved.
#
# This software is proprietary and confidential. Unauthorized copying,
# distribution, or use of this software is strictly prohibited.

import gradio as gr
import json

def run_mission(target, mission_type):
    # Your red team logic here
    results = f"Scanning {target} with {mission_type} mission..."
    return results

def load_config():
    with open('redteam-agents.json', 'r') as f:
        config = json.load(f)
    agents = [a['name'] for a in config['agents']]
    workflows = [w['name'] for w in config['workflows']]
    return agents, workflows

agents, workflows = load_config()

interface = gr.Interface(
    fn=run_mission,
    inputs=[
        gr.Textbox(label="Target", value="demo.test.com"),
        gr.Dropdown(choices=workflows, label="Mission Type", value="QuickRecon")
    ],
    outputs="text",
    title="AI Red Team Control Panel",
    description="AI-powered penetration testing"
)

interface.launch(share=True)
