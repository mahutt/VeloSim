/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import React from 'react';
import { Button } from '~/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';

interface OverwriteSaveDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOverwrite: () => void;
  onSaveAsNew: () => void;
  scenarioName: string;
}

const OverwriteSaveDialog: React.FC<OverwriteSaveDialogProps> = ({
  open,
  onOpenChange,
  onOverwrite,
  onSaveAsNew,
  scenarioName,
}) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Overwrite or Save As New?</DialogTitle>
        <DialogDescription>
          You are editing the scenario <strong>{scenarioName}</strong>.
          <br />
          Would you like to overwrite the existing scenario or save as a new
          one?
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button onClick={() => onOpenChange(false)} variant="outline">
          Cancel
        </Button>
        <Button onClick={onSaveAsNew} variant="secondary">
          Save As New
        </Button>
        <Button onClick={onOverwrite} variant="default">
          Overwrite
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);

export default OverwriteSaveDialog;
