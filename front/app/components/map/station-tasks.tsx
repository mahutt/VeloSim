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
import type { PopulatedStation } from './selected-item-bar';

export function StationTasks({ station }: { station: PopulatedStation }) {
  const { engine } = useSimulation();
  const taskIds = station.tasks.map((task) => task.id);
  const { selectedTaskIds, handleTaskSelect, selectForDrag } =
    useTaskMassSelect(taskIds, station.id);

  return (
    <>
      <p className="text-sm text-muted-foreground">
        {selectedTaskIds.length > 0
          ? `Tasks (${selectedTaskIds.length}/${station.tasks.length} selected)`
          : `Tasks (${station.tasks.length})`}
      </p>
      {station.tasks.map((task, index) => {
        return (
          <TaskItem
            key={task.id}
            task={task}
            stationName={station.name}
            isSelected={selectedTaskIds.includes(task.id)}
            onSelect={(event) => handleTaskSelect(task.id, index, event)}
            onDragStart={() => selectForDrag(task.id, index)}
            getDragTaskIds={() =>
              selectedTaskIds.includes(task.id) ? selectedTaskIds : [task.id]
            }
            onUnassign={
              task.assignedDriverId
                ? () => {
                    if (!task.assignedDriverId) return;
                    engine.requestUnassignment(task.assignedDriverId, task.id);
                  }
                : undefined
            }
          />
        );
      })}
    </>
  );
}
