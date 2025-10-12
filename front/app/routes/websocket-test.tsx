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

import { useState } from 'react';
import { useSimulationLifecycle, useSimulationFrames } from '../hooks';
import { Button } from '~/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '~/components/ui/card';
import { Separator } from '~/components/ui/separator';

export default function WebSocketTest() {
  const {
    simId,
    isRunning,
    error: simError,
    start,
    stop,
  } = useSimulationLifecycle();
  const {
    frames,
    connected,
    error: wsError,
    clearFrames,
  } = useSimulationFrames(simId);
  const [maxFrames, setMaxFrames] = useState(50);

  const displayedFrames = frames.slice(-maxFrames);
  const latestFrame = frames[frames.length - 1];

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-6xl">
      <div>
        <h1 className="text-3xl font-bold mb-2">WebSocket Frame Stream Test</h1>
        <p className="text-muted-foreground">
          Real-time simulation frame streaming
        </p>
      </div>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Controls</CardTitle>
          <CardDescription>
            Start and stop simulations, manage frame display
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-center">
            <Button
              onClick={isRunning ? stop : start}
              variant={isRunning ? 'destructive' : 'default'}
              size="lg"
            >
              {isRunning ? 'Stop Simulation' : 'Start Simulation'}
            </Button>
            <Button
              onClick={clearFrames}
              disabled={frames.length === 0}
              variant="outline"
              size="lg"
            >
              Clear Frames
            </Button>
            <div className="flex items-center gap-2">
              <label htmlFor="max-frames" className="text-sm font-medium">
                Max display:
              </label>
              <input
                id="max-frames"
                type="number"
                value={maxFrames}
                onChange={(e) =>
                  setMaxFrames(Math.max(1, parseInt(e.target.value) || 50))
                }
                min="1"
                max="1000"
                className="w-20 px-3 py-2 border rounded-md text-sm"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Status</CardTitle>
          <CardDescription>
            Current simulation and WebSocket connection status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-md">
              <span className="text-sm font-medium">Simulation:</span>
              <span className="text-sm font-semibold">
                {isRunning ? ' Running' : ' Stopped'}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-md">
              <span className="text-sm font-medium">WebSocket:</span>
              <span className="text-sm font-semibold">
                {connected ? ' Connected' : ' Disconnected'}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-md">
              <span className="text-sm font-medium">Simulation ID:</span>
              <code className="text-xs bg-background px-2 py-1 rounded border">
                {simId || 'N/A'}
              </code>
            </div>
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-md">
              <span className="text-sm font-medium">Total Frames:</span>
              <span className="text-sm font-bold">{frames.length}</span>
            </div>
          </div>
          {(simError || wsError) && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700 font-medium">
                {' '}
                Error: {simError || wsError}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {latestFrame && (
        <Card>
          <CardHeader>
            <CardTitle>Latest Frame</CardTitle>
            <CardDescription>Most recently received frame data</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 font-mono text-sm bg-muted/50 p-4 rounded-md">
              <div className="flex justify-between border-b border-border pb-2">
                <span className="font-semibold">Sequence:</span>
                <span>#{latestFrame.seq_numb}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="font-semibold">Timestamp:</span>
                <span>{latestFrame.timestamp}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="font-semibold">Payload:</span>
                <span className="text-muted-foreground">
                  {latestFrame.payload}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>
            Frame History
            {frames.length > maxFrames && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                (showing last {maxFrames} of {frames.length})
              </span>
            )}
          </CardTitle>
          <CardDescription>
            Real-time stream of simulation frames
          </CardDescription>
        </CardHeader>
        <CardContent>
          {frames.length === 0 ? (
            <p className="text-muted-foreground text-center py-8 italic">
              No frames received yet. Start a simulation to begin receiving
              frames.
            </p>
          ) : (
            <div className="border rounded-md max-h-[400px] overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 sticky top-0">
                  <tr className="border-b">
                    <th className="text-left p-3 font-medium">Seq #</th>
                    <th className="text-left p-3 font-medium">Timestamp</th>
                    <th className="text-left p-3 font-medium">Payload</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedFrames.map((frame, index) => (
                    <tr
                      key={frame.seq_numb + '-' + index}
                      className="border-b hover:bg-muted/30"
                    >
                      <td className="p-3 font-semibold">#{frame.seq_numb}</td>
                      <td className="p-3 text-muted-foreground">
                        {frame.timestamp}
                      </td>
                      <td className="p-3 font-mono text-xs">{frame.payload}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle> Instructions</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-2 text-sm list-decimal list-inside">
            <li>
              Make sure the backend is running:{' '}
              <code className="bg-muted px-1.5 py-0.5 rounded text-xs">
                python -m back.main
              </code>
            </li>
            <li>
              Click &ldquo;Start Simulation&rdquo; to create a new simulation
            </li>
            <li>
              Watch frames arrive in real-time (approximately 1 per second)
            </li>
            <li>Click &ldquo;Stop Simulation&rdquo; to end the simulation</li>
            <li>Use &ldquo;Clear Frames&rdquo; to reset the frame history</li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
