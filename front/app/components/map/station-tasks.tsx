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

import { TaskItem } from '~/components/task/task-item';
import { useSimulation } from '~/providers/simulation-provider';
import { useTaskMassSelect } from '~/hooks/use-task-mass-select';
import { useAutoScroll } from '~/hooks/use-auto-scroll';
import type { PopulatedStation } from './selected-item-bar';
import { ScrollArea } from '~/components/ui/scroll-area';
import usePreferences from '~/hooks/use-preferences';
import { formatTranslation } from '~/lib/i18n';

export function StationTasks({ station }: { station: PopulatedStation }) {
  const { engine } = useSimulation();
  const { t } = usePreferences();
  const taskIds = station.tasks.map((task) => task.id);
  const {
    selectedTaskIds,
    isDragSelecting,
    handleTaskSelect,
    selectForDrag,
    startDragSelect,
    dragSelectEnter,
  } = useTaskMassSelect(taskIds, station.id);
  const { containerRef, handleMouseMove } = useAutoScroll(isDragSelecting);

  return (
    <>
      <p className="px-5 text-sm text-muted-foreground">
        {selectedTaskIds.length > 0
          ? formatTranslation(t.map.labels.tasksSelectedCount, {
              selected: selectedTaskIds.length,
              total: station.tasks.length,
            })
          : formatTranslation(t.map.labels.tasksCount, {
              count: station.tasks.length,
            })}
      </p>
      <ScrollArea className="mx-2">
        <div
          ref={containerRef}
          onMouseMove={handleMouseMove}
          className="max-h-50 px-3 space-y-1"
        >
          {station.tasks.map((task, index) => {
            const assignedDriverId = task.assignedDriverId;

            return (
              <div
                key={task.id}
                onContextMenu={(e) => e.preventDefault()}
                onMouseDown={(e) => {
                  if (e.button === 2) {
                    e.preventDefault();
                    startDragSelect(task.id, e.ctrlKey || e.metaKey);
                  }
                }}
                onMouseEnter={() => dragSelectEnter(task.id)}
              >
                <TaskItem
                  task={task}
                  stationName={station.name}
                  isSelected={selectedTaskIds.includes(task.id)}
                  onSelect={(event) => handleTaskSelect(task.id, index, event)}
                  onDragStart={() => selectForDrag(task.id)}
                  getDragTaskIds={() =>
                    selectedTaskIds.includes(task.id)
                      ? selectedTaskIds
                      : [task.id]
                  }
                  onUnassign={
                    assignedDriverId
                      ? () => {
                          engine.requestUnassignment(assignedDriverId, [
                            task.id,
                          ]);
                        }
                      : undefined
                  }
                />
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </>
  );
}
