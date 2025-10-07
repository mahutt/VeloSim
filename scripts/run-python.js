#!/usr/bin/env node

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

/**
 * Cross-platform Python runner for VeloSim
 * Flexibly detects and uses the appropriate Python interpreter based on developer preference:
 * 1. Active virtual environment Python
 * 2. System Python
 * 3. Project .venv Python
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Detect operating system
const isWindows = process.platform === 'win32';

function findPythonExecutable() {
  // Priority 1: Check if we're in an active virtual environment
  if (process.env.VIRTUAL_ENV) {
    const venvPython = isWindows
      ? path.join(process.env.VIRTUAL_ENV, 'Scripts', 'python.exe')
      : path.join(process.env.VIRTUAL_ENV, 'bin', 'python');

    if (fs.existsSync(venvPython)) {
      return venvPython;
    }
  }

  // Priority 2: If no virtual environment is active, use system Python
  if (!process.env.VIRTUAL_ENV) {
    return 'python';
  }

  // Priority 3: Fallback - check for .venv directories if VIRTUAL_ENV is set but corrupted
  const possibleVenvPaths = [
    path.join(process.cwd(), '.venv'),                    // Current directory
    path.join(process.cwd(), '..', '.venv'),              // Parent directory (from back/)
    path.join(__dirname, '..', '.venv'),                  // Project root (from scripts/)
  ];

  for (const venvPath of possibleVenvPaths) {
    if (fs.existsSync(venvPath)) {
      const venvPython = isWindows
        ? path.join(venvPath, 'Scripts', 'python.exe')
        : path.join(venvPath, 'bin', 'python');

      if (fs.existsSync(venvPython)) {
        return venvPython;
      }
    }
  }

  // Final fallback: Use system Python
  return 'python';
}

function runPython(args) {
  const pythonExecutable = findPythonExecutable();

  const child = spawn(pythonExecutable, args, {
    stdio: 'inherit',
    shell: true,
    cwd: process.cwd()
  });

  child.on('close', (code) => {
    process.exit(code);
  });

  child.on('error', (err) => {
    console.error(`ERROR [velosim.run-python] Failed to start Python: ${err.message}`);
    process.exit(1);
  });
}

// Get command line arguments (skip node and script name)
const args = process.argv.slice(2);

if (args.length === 0) {
  console.error('Usage: node run-python.js <python-args>');
  console.error('Example: node run-python.js -m uvicorn main:app --reload');
  process.exit(1);
}

runPython(args);
