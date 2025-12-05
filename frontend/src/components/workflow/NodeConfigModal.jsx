/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect } from 'react';
import { Settings, Save, X } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';

/**
 * Node Configuration Modal
 * Allows editing node parameters with validation
 */
function NodeConfigModal({ node, toolSchema, open, onClose, onSave }) {
  const [params, setParams] = useState({});
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (node) {
      setParams(node.data.params || {});
      setErrors({});
    }
  }, [node]);

  const validateParams = () => {
    const newErrors = {};
    
    if (!toolSchema) return newErrors;

    // Check required fields
    const required = toolSchema.input_schema?.required || [];
    required.forEach((field) => {
      if (!params[field] || params[field].trim() === '') {
        newErrors[field] = 'This field is required';
      }
    });

    return newErrors;
  };

  const handleSave = () => {
    const validationErrors = validateParams();
    
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    onSave(node.id, params);
    onClose();
  };

  const handleChange = (field, value) => {
    setParams({ ...params, [field]: value });
    // Clear error for this field
    if (errors[field]) {
      setErrors({ ...errors, [field]: undefined });
    }
  };

  if (!node || !toolSchema) return null;

  const properties = toolSchema.input_schema?.properties || {};
  const required = toolSchema.input_schema?.required || [];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Configure Node
          </DialogTitle>
          <DialogDescription>
            {node.data.mcp_server}.{node.data.tool}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
          {Object.entries(properties).map(([key, schema]) => {
            const isRequired = required.includes(key);
            const isLongText = schema.description && schema.description.length > 100;

            return (
              <div key={key} className="space-y-2">
                <Label htmlFor={key}>
                  {key}
                  {isRequired && (
                    <span className="text-destructive ml-1">*</span>
                  )}
                </Label>
                
                {schema.description && (
                  <p className="text-xs text-muted-foreground">
                    {schema.description}
                  </p>
                )}

                {isLongText || schema.type === 'string' && key.includes('prompt') ? (
                  <Textarea
                    id={key}
                    value={params[key] || ''}
                    onChange={(e) => handleChange(key, e.target.value)}
                    placeholder={`Enter ${key}...`}
                    className={errors[key] ? 'border-destructive' : ''}
                    rows={4}
                  />
                ) : (
                  <Input
                    id={key}
                    value={params[key] || ''}
                    onChange={(e) => handleChange(key, e.target.value)}
                    placeholder={`Enter ${key}...`}
                    className={errors[key] ? 'border-destructive' : ''}
                  />
                )}

                {errors[key] && (
                  <Alert variant="destructive" className="py-2">
                    <AlertDescription className="text-sm">
                      {errors[key]}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            );
          })}

          {Object.keys(properties).length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              This tool has no configurable parameters.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button onClick={handleSave}>
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default NodeConfigModal;
