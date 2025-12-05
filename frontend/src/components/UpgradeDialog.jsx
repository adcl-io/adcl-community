import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { Download, AlertCircle, CheckCircle2, Loader2, Archive } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function UpgradeDialog({ open, onOpenChange }) {
  const [updateInfo, setUpdateInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Check for updates when dialog opens
  useEffect(() => {
    if (open) {
      checkForUpdates();
    }
  }, [open]);

  const checkForUpdates = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/system/updates/check`);
      if (!response.ok) {
        throw new Error('Failed to check for updates');
      }

      const data = await response.json();
      setUpdateInfo(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const performUpgrade = async () => {
    if (!updateInfo || !updateInfo.update_available) {
      return;
    }

    setUpgrading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/system/updates/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_version: updateInfo.latest_version,
          auto_backup: true,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.error || 'Upgrade failed');
      }

      const result = await response.json();

      if (result.status === 'ready') {
        setSuccess(true);
        // Show next steps
        setUpdateInfo({ ...updateInfo, next_steps: result.next_steps });
      } else {
        throw new Error(result.error || 'Upgrade preparation failed');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUpgrading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Platform Upgrade
          </DialogTitle>
          <DialogDescription>
            Check for and apply platform updates
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-2">Checking for updates...</span>
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                Backup created successfully! Ready to upgrade.
              </AlertDescription>
            </Alert>
          )}

          {!loading && updateInfo && !updateInfo.error && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">
                    Current Version
                  </div>
                  <div className="text-2xl font-bold">
                    {updateInfo.current_version}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">
                    Latest Version
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-2xl font-bold">
                      {updateInfo.latest_version}
                    </div>
                    {updateInfo.update_available && (
                      <Badge variant="default" className="bg-green-600">
                        New
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              {updateInfo.update_available && (
                <>
                  {updateInfo.release_name && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium">Release Name</div>
                      <div className="text-lg">{updateInfo.release_name}</div>
                    </div>
                  )}

                  {updateInfo.published_at && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">
                        Published
                      </div>
                      <div>{formatDate(updateInfo.published_at)}</div>
                    </div>
                  )}

                  {updateInfo.release_notes && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium">Release Notes</div>
                      <div className="bg-muted p-4 rounded-md max-h-48 overflow-y-auto">
                        <pre className="text-sm whitespace-pre-wrap font-mono">
                          {updateInfo.release_notes}
                        </pre>
                      </div>
                    </div>
                  )}

                  {updateInfo.next_steps && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium">Next Steps</div>
                      <Alert>
                        <Archive className="h-4 w-4" />
                        <AlertDescription>
                          <ol className="list-decimal list-inside space-y-1">
                            {updateInfo.next_steps.map((step, index) => (
                              <li key={index} className="text-sm">
                                {step}
                              </li>
                            ))}
                          </ol>
                        </AlertDescription>
                      </Alert>
                    </div>
                  )}
                </>
              )}

              {!updateInfo.update_available && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertDescription>
                    You are running the latest version of ADCL platform.
                  </AlertDescription>
                </Alert>
              )}
            </>
          )}

          {!loading && updateInfo?.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{updateInfo.error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={upgrading}
          >
            Close
          </Button>

          {!loading && updateInfo?.update_available && !success && (
            <Button
              onClick={performUpgrade}
              disabled={upgrading}
              className="bg-green-600 hover:bg-green-700"
            >
              {upgrading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Preparing Upgrade...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  Prepare Upgrade
                </>
              )}
            </Button>
          )}

          {!loading && !updateInfo?.update_available && (
            <Button onClick={checkForUpdates} variant="outline">
              Recheck
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
