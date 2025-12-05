/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect } from 'react';
import { Save, FolderOpen, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

/**
 * Workflow Toolbar Component
 * Provides workflow actions like save, load, and examples
 */
function WorkflowToolbar({ 
  onSave, 
  onLoad, 
  onListWorkflows,
  onDeleteWorkflow,
  workflowName,
  onWorkflowNameChange 
}) {
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [savedWorkflows, setSavedWorkflows] = useState([]);
  const [saveName, setSaveName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');

  // Load workflows when dialog opens
  useEffect(() => {
    if (loadDialogOpen && onListWorkflows) {
      onListWorkflows().then(setSavedWorkflows).catch(console.error);
    }
  }, [loadDialogOpen, onListWorkflows]);

  const handleSave = async () => {
    if (!saveName.trim()) return;
    try {
      await onSave(saveName, saveDescription);
      toast.success('Workflow saved successfully');
      setSaveDialogOpen(false);
      setSaveName('');
      setSaveDescription('');
    } catch (error) {
      console.error('Failed to save workflow:', error);
      toast.error(`Failed to save workflow: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleLoad = async (filename) => {
    try {
      await onLoad(filename);
      toast.success('Workflow loaded successfully');
      setLoadDialogOpen(false);
    } catch (error) {
      console.error('Failed to load workflow:', error);
      toast.error(`Failed to load workflow: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDelete = async (filename) => {
    if (!confirm('Delete this workflow?')) return;
    try {
      await onDeleteWorkflow(filename);
      toast.success('Workflow deleted successfully');
      setSavedWorkflows(workflows => workflows.filter(w => w.filename !== filename));
    } catch (error) {
      console.error('Failed to delete workflow:', error);
      toast.error(`Failed to delete workflow: ${error.response?.data?.detail || error.message}`);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Workflow Actions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Button 
            onClick={() => setSaveDialogOpen(true)} 
            variant="default"
            className="w-full justify-start"
          >
            <Save className="mr-2 h-4 w-4" />
            Save Workflow
          </Button>
          <Button 
            onClick={() => setLoadDialogOpen(true)} 
            variant="outline"
            className="w-full justify-start"
          >
            <FolderOpen className="mr-2 h-4 w-4" />
            Load Workflow
          </Button>
        </CardContent>
      </Card>

      {/* Save Dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Workflow</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="workflow-name">Workflow Name</Label>
              <Input
                id="workflow-name"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="My Workflow"
              />
            </div>
            <div>
              <Label htmlFor="workflow-description">Description (optional)</Label>
              <Input
                id="workflow-description"
                value={saveDescription}
                onChange={(e) => setSaveDescription(e.target.value)}
                placeholder="What does this workflow do?"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!saveName.trim()}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Load Dialog */}
      <Dialog open={loadDialogOpen} onOpenChange={setLoadDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Load Workflow</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {savedWorkflows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No saved workflows</p>
            ) : (
              savedWorkflows.map((workflow) => (
                <div
                  key={workflow.filename}
                  className="flex items-center justify-between p-3 border rounded hover:bg-accent"
                >
                  <div className="flex-1 cursor-pointer" onClick={() => handleLoad(workflow.filename)}>
                    <div className="font-medium">{workflow.name}</div>
                    {workflow.description && (
                      <div className="text-sm text-muted-foreground">{workflow.description}</div>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(workflow.filename);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLoadDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default WorkflowToolbar;
