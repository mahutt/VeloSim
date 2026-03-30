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

import { MoreHorizontal, Upload } from 'lucide-react';
import { Badge } from '~/components/ui/badge';
import { Button } from '~/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '~/components/ui/dropdown-menu';
import { Input } from '~/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '~/components/ui/table';
import usePreferences from '~/hooks/use-preferences';
import type { TrafficTemplate } from '~/types';

type TrafficTemplateWithDisplay = TrafficTemplate & {
  updatedDisplay: string;
};

interface DataTableProps {
  templates: TrafficTemplateWithDisplay[];
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onUploadClick: () => void;
  onUploadFileSelected: (file: File | null) => void;
  onEditClick: (template: TrafficTemplate) => void;
  onDownloadClick: (template: TrafficTemplate) => void;
  onDeleteClick: (template: TrafficTemplate) => void;
  pageIndex: number;
  totalPages: number;
  onPreviousPage: () => void;
  onNextPage: () => void;
  uploadInputRef: React.RefObject<HTMLInputElement | null>;
  editFileInputRef: React.RefObject<HTMLInputElement | null>;
  onEditFileChange: (file: File | null) => void;
  PAGE_SIZE: number;
}

export function DataTable(props: DataTableProps) {
  const {
    templates,
    searchQuery,
    onSearchChange,
    onUploadClick,
    onUploadFileSelected,
    onEditClick,
    onDownloadClick,
    onDeleteClick,
    pageIndex,
    totalPages,
    onPreviousPage,
    onNextPage,
    uploadInputRef,
    editFileInputRef,
    onEditFileChange,
    PAGE_SIZE,
  } = props;

  const { t } = usePreferences();

  const start = pageIndex * PAGE_SIZE;
  const paginatedTemplates = templates.slice(start, start + PAGE_SIZE);

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center gap-4">
          <Input
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={t.trafficTemplates.filterPlaceholder}
            className="max-w-sm"
          />
          <Button onClick={onUploadClick}>
            <Upload />
            {t.trafficTemplates.upload}
          </Button>
        </div>

        <input
          ref={uploadInputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            onUploadFileSelected(file);
            event.target.value = '';
          }}
        />

        <input
          ref={editFileInputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            onEditFileChange(file);
            event.target.value = '';
          }}
        />

        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t.trafficTemplates.column.key}</TableHead>
                <TableHead>{t.trafficTemplates.column.description}</TableHead>
                <TableHead>{t.trafficTemplates.column.updated}</TableHead>
                <TableHead className="text-right" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {templates.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    {t.trafficTemplates.noResults}
                  </TableCell>
                </TableRow>
              ) : (
                paginatedTemplates.map((template) => (
                  <TableRow key={template.key}>
                    <TableCell>
                      <Badge>{template.key}</Badge>
                    </TableCell>
                    <TableCell className="max-w-lg whitespace-pre-wrap wrap-break-word">
                      {template.description || '-'}
                    </TableCell>
                    <TableCell>{template.updatedDisplay}</TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            className="h-8 w-8 p-0"
                            data-testid={`template-actions-${template.key}`}
                          >
                            <span className="sr-only">
                              {t.trafficTemplates.actions.openMenu}
                            </span>
                            <MoreHorizontal />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => onEditClick(template)}
                          >
                            {t.trafficTemplates.actions.edit}
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => onDownloadClick(template)}
                          >
                            {t.trafficTemplates.actions.download}
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => onDeleteClick(template)}
                          >
                            {t.trafficTemplates.actions.delete}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        <div className="flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onPreviousPage}
            disabled={pageIndex === 0}
          >
            {t.users.previous}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onNextPage}
            disabled={pageIndex >= totalPages - 1}
          >
            {t.users.next}
          </Button>
        </div>
      </div>
    </>
  );
}
