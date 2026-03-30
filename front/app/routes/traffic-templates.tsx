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

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
} from 'react';
import { useNavigate } from 'react-router';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import api from '~/api';
import { DataTable } from '~/components/traffic-templates/data-table';
import Page from '~/components/page';
import { Button } from '~/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';
import { Input } from '~/components/ui/input';
import { Textarea } from '~/components/ui/textarea';
import useAuth from '~/hooks/use-auth';
import useError from '~/hooks/use-error';
import usePreferences from '~/hooks/use-preferences';
import type {
  TrafficTemplate,
  TrafficTemplateCreateRequest,
  TrafficTemplateListResponse,
  TrafficTemplateUpdateRequest,
  TrafficTemplateValidationResponse,
} from '~/types';

const KEY_PATTERN = /^[a-z0-9_-]{1,32}$/;
const PAGE_SIZE = 10;

type TrafficTemplateRow = TrafficTemplate & {
  updatedDisplay: string;
  searchText: string;
};

export function meta() {
  return [{ title: 'Traffic Templates' }];
}

function isCsvFile(file: File): boolean {
  return file.name.toLowerCase().endsWith('.csv');
}

function templateKeyFromFile(fileName: string): string {
  const baseName = fileName
    .replace(/\.[^/.]+$/, '')
    .trim()
    .toLowerCase();
  const slug = baseName
    .replace(/\s+/g, '_')
    .replace(/[^a-z0-9_-]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '');

  return (slug || 'template_key').slice(0, 32);
}

function formatApiError(error: unknown): string {
  if (error && typeof error === 'object') {
    const errorObj = error as {
      response?: { data?: { detail?: unknown } };
      message?: string;
    };

    const detail = errorObj.response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (detail && typeof detail === 'object') {
      try {
        return JSON.stringify(detail);
      } catch {
        return 'Unknown API error';
      }
    }

    return errorObj.message ?? 'Unknown API error';
  }

  return 'Unknown API error';
}

function formatTemplateTimestamp(timestamp: string): string {
  // Parse timestamp as UTC if timezone info is missing
  let dateString = timestamp;
  if (
    !timestamp.includes('Z') &&
    !timestamp.includes('+') &&
    !/[+-]\d{2}:\d{2}$/.test(timestamp)
  ) {
    dateString = timestamp + 'Z';
  }

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }

  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/Toronto',
    timeZoneName: 'short',
  }).format(date);
}

async function fetchAllTemplates(): Promise<TrafficTemplate[]> {
  const templates: TrafficTemplate[] = [];
  let page = 1;
  const perPage = 20;
  let totalPages = 1;

  while (page <= totalPages) {
    const response = await api.get<TrafficTemplateListResponse>(
      `/trafficTemplates?skip=${(page - 1) * perPage}&limit=${perPage}`
    );
    const data = response.data;
    templates.push(...data.templates);
    totalPages = data.total_pages;
    page += 1;
  }

  return templates;
}

export default function TrafficTemplates() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const { displayError } = useError();
  const { t } = usePreferences();

  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const editFileInputRef = useRef<HTMLInputElement | null>(null);

  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState<TrafficTemplateRow[]>([]);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [pageIndex, setPageIndex] = useState(0);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createKey, setCreateKey] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createFile, setCreateFile] = useState<File | null>(null);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createInlineError, setCreateInlineError] = useState<string | null>(
    null
  );

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<TrafficTemplate | null>(null);
  const [editDescription, setEditDescription] = useState('');
  const [editFile, setEditFile] = useState<File | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editInlineError, setEditInlineError] = useState<string | null>(null);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TrafficTemplate | null>(
    null
  );
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const sortedTemplates = useMemo(
    () => [...templates].sort((a, b) => a.key.localeCompare(b.key)),
    [templates]
  );

  const filteredTemplates = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return sortedTemplates;
    }

    return sortedTemplates.filter((template) =>
      template.searchText.includes(normalizedQuery)
    );
  }, [searchQuery, sortedTemplates]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredTemplates.length / PAGE_SIZE)
  );

  useEffect(() => {
    setPageIndex(0);
  }, [searchQuery]);

  useEffect(() => {
    if (pageIndex >= totalPages) {
      setPageIndex(totalPages - 1);
    }
  }, [pageIndex, totalPages]);

  const normalizedCreateKey = createKey.trim();
  const createKeyValid = KEY_PATTERN.test(normalizedCreateKey);
  const canCreateTemplate = !!createFile && createKeyValid && !createSubmitting;

  const initialEditDescription = (editTarget?.description ?? '').trim();
  const currentEditDescription = editDescription.trim();
  const hasEditChanges =
    !!editFile || initialEditDescription !== currentEditDescription;
  const canUpdateTemplate = hasEditChanges && !editSubmitting;

  const formatSelectedFile = useCallback(
    (name: string) => t.trafficTemplates.selectedFile.replace('{{name}}', name),
    [t.trafficTemplates.selectedFile]
  );

  const loadErrorTitle = t.trafficTemplates.error.loadTitle;
  const loadErrorDescription = t.trafficTemplates.error.loadDescription;
  const unauthorizedTitle = t.trafficTemplates.error.unauthorizedTitle;
  const unauthorizedDescription =
    t.trafficTemplates.error.unauthorizedDescription;

  const loadTemplates = useCallback(async () => {
    try {
      const data = await fetchAllTemplates();
      setTemplates(
        data.map((template) => ({
          ...template,
          updatedDisplay: formatTemplateTimestamp(template.date_updated),
          searchText:
            `${template.key} ${template.description ?? ''}`.toLowerCase(),
        }))
      );
    } catch (error) {
      displayError(
        loadErrorTitle,
        `${loadErrorDescription}\n${formatApiError(error)}`,
        loadTemplates
      );
    }
  }, [displayError, loadErrorDescription, loadErrorTitle]);

  useEffect(() => {
    if (authLoading) {
      return;
    }

    if (!user?.is_admin) {
      displayError(unauthorizedTitle, unauthorizedDescription);
      navigate('/', { replace: true });
      return;
    }

    setLoading(true);
    loadTemplates().finally(() => setLoading(false));
  }, [
    authLoading,
    user?.is_admin,
    navigate,
    displayError,
    unauthorizedDescription,
    unauthorizedTitle,
    loadTemplates,
  ]);

  const validateTemplateContent = useCallback(
    async (content: string): Promise<string | null> => {
      try {
        const response = await api.post<TrafficTemplateValidationResponse>(
          '/trafficTemplates/validate',
          { content }
        );

        if (response.data.valid) {
          return null;
        }

        return response.data.errors.length
          ? response.data.errors.map((x) => `• ${x}`).join('\n')
          : t.trafficTemplates.error.parseDescription;
      } catch (error) {
        return formatApiError(error);
      }
    },
    [t]
  );

  const resetCreateDialog = () => {
    setCreateDialogOpen(false);
    setCreateKey('');
    setCreateDescription('');
    setCreateFile(null);
    setCreateInlineError(null);
  };

  const handleUploadButton = () => {
    uploadInputRef.current?.click();
  };

  const handleCreateFilePick = (file: File | null) => {
    if (!file) {
      return;
    }

    if (!isCsvFile(file)) {
      setCreateInlineError(t.trafficTemplates.validation.csvType);
      setCreateDialogOpen(true);
      return;
    }

    setCreateInlineError(null);
    setCreateFile(file);
    setCreateKey((prev) => prev || templateKeyFromFile(file.name));
    setCreateDialogOpen(true);
  };

  const handleCreateSubmit = async () => {
    setCreateInlineError(null);
    const normalizedKey = createKey.trim();

    if (!normalizedKey) {
      setCreateInlineError(t.trafficTemplates.validation.keyRequired);
      return;
    }

    if (!KEY_PATTERN.test(normalizedKey)) {
      setCreateInlineError(t.trafficTemplates.validation.keyInvalid);
      return;
    }

    if (!createFile) {
      setCreateInlineError(t.trafficTemplates.validation.csvRequired);
      return;
    }

    if (!isCsvFile(createFile)) {
      setCreateInlineError(t.trafficTemplates.validation.csvType);
      return;
    }

    setCreateSubmitting(true);
    try {
      const content = await createFile.text();

      const validationError = await validateTemplateContent(content);
      if (validationError) {
        setCreateInlineError(validationError);
        return;
      }

      const payload: TrafficTemplateCreateRequest = {
        key: normalizedKey,
        content,
        description: createDescription.trim() || undefined,
      };

      await api.post('/trafficTemplates', payload);
      toast.success(t.trafficTemplates.success.created);
      await loadTemplates();
      resetCreateDialog();
    } catch (error) {
      setCreateInlineError(formatApiError(error));
    } finally {
      setCreateSubmitting(false);
    }
  };

  const openEditDialog = (template: TrafficTemplate) => {
    setEditTarget(template);
    setEditDescription(template.description ?? '');
    setEditFile(null);
    setEditInlineError(null);
    setEditDialogOpen(true);
  };

  const handleEditSubmit = async () => {
    if (!editTarget) {
      return;
    }

    setEditInlineError(null);
    setEditSubmitting(true);
    try {
      const payload: TrafficTemplateUpdateRequest = {
        description:
          editDescription.trim() === '' ? null : editDescription.trim(),
      };

      if (editFile) {
        if (!isCsvFile(editFile)) {
          setEditInlineError(t.trafficTemplates.validation.csvType);
          return;
        }

        const content = await editFile.text();
        const validationError = await validateTemplateContent(content);
        if (validationError) {
          setEditInlineError(validationError);
          return;
        }

        payload.content = content;
      }

      await api.put(
        `/trafficTemplates/${encodeURIComponent(editTarget.key)}`,
        payload
      );
      toast.success(t.trafficTemplates.success.updated);
      setEditDialogOpen(false);
      setEditTarget(null);
      setEditFile(null);
      await loadTemplates();
    } catch (error) {
      setEditInlineError(formatApiError(error));
    } finally {
      setEditSubmitting(false);
    }
  };

  const openDeleteDialog = (template: TrafficTemplate) => {
    setDeleteTarget(template);
    setDeleteDialogOpen(true);
  };

  const handleDeleteSubmit = async () => {
    if (!deleteTarget) {
      return;
    }

    setDeleteSubmitting(true);
    try {
      await api.delete(
        `/trafficTemplates/${encodeURIComponent(deleteTarget.key)}`
      );
      toast.success(t.trafficTemplates.success.deleted);
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await loadTemplates();
    } catch (error) {
      displayError(t.trafficTemplates.error.deleteTitle, formatApiError(error));
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const downloadTemplate = (template: TrafficTemplate) => {
    try {
      const blob = new Blob([template.content], {
        type: 'text/csv;charset=utf-8;',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${template.key}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success(t.trafficTemplates.success.downloaded);
    } catch {
      toast.error(t.trafficTemplates.error.downloadTitle);
    }
  };

  const onDragOver = (event: DragEvent<HTMLDivElement>) => {
    if (!event.dataTransfer.types.includes('Files')) {
      return;
    }

    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
    setIsDraggingFile(true);
  };

  const onDragLeave = (event: DragEvent<HTMLDivElement>) => {
    if (!event.dataTransfer.types.includes('Files')) {
      return;
    }

    const relatedTarget = event.relatedTarget as Node | null;
    const isLeavingContainer =
      !relatedTarget || !event.currentTarget.contains(relatedTarget);

    if (isLeavingContainer) {
      event.preventDefault();
      setIsDraggingFile(false);
    }
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    if (!event.dataTransfer.files?.length) {
      return;
    }

    event.preventDefault();
    setIsDraggingFile(false);
    handleCreateFilePick(event.dataTransfer.files[0]);
  };

  if (authLoading || (loading && user?.is_admin)) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <Loader2 className="animate-spin text-gray-300 w-16 h-16" />
      </div>
    );
  }

  if (!user?.is_admin) {
    return null;
  }

  return (
    <Page>
      <div onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
        {isDraggingFile && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm pointer-events-none">
            <p className="text-2xl font-bold">
              {t.trafficTemplates.dropToImport}
            </p>
          </div>
        )}

        <div className="flex flex-col gap-2">
          <div className="text-xl">{t.trafficTemplates.title}</div>

          <DataTable
            templates={filteredTemplates}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onUploadClick={handleUploadButton}
            onUploadFileSelected={handleCreateFilePick}
            onEditClick={openEditDialog}
            onDownloadClick={downloadTemplate}
            onDeleteClick={openDeleteDialog}
            pageIndex={pageIndex}
            totalPages={totalPages}
            onPreviousPage={() => setPageIndex((prev) => Math.max(0, prev - 1))}
            onNextPage={() =>
              setPageIndex((prev) => Math.min(totalPages - 1, prev + 1))
            }
            uploadInputRef={uploadInputRef}
            editFileInputRef={editFileInputRef}
            onEditFileChange={(file) => {
              setEditFile(file);
              setEditInlineError(null);
            }}
            PAGE_SIZE={PAGE_SIZE}
          />
        </div>

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t.trafficTemplates.dialog.createTitle}</DialogTitle>
              <DialogDescription>
                {t.trafficTemplates.dialog.createDescription}
              </DialogDescription>
            </DialogHeader>

            {createInlineError && (
              <p className="text-sm text-destructive whitespace-pre-line">
                {createInlineError}
              </p>
            )}

            <div className="space-y-3">
              <div className="space-y-2">
                <label htmlFor="template-key" className="text-sm font-medium">
                  {t.trafficTemplates.key}
                </label>
                <Input
                  id="template-key"
                  value={createKey}
                  placeholder={t.trafficTemplates.keyPlaceholder}
                  onChange={(event) => setCreateKey(event.target.value)}
                  disabled={createSubmitting}
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="template-description"
                  className="text-sm font-medium"
                >
                  {t.trafficTemplates.description}
                </label>
                <Textarea
                  id="template-description"
                  value={createDescription}
                  placeholder={t.trafficTemplates.descriptionPlaceholder}
                  onChange={(event) => setCreateDescription(event.target.value)}
                  disabled={createSubmitting}
                />
              </div>

              {createFile && (
                <p className="text-xs text-muted-foreground">
                  {formatSelectedFile(createFile.name)}
                </p>
              )}
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button
                  variant="outline"
                  onClick={resetCreateDialog}
                  disabled={createSubmitting}
                >
                  {t.common.cancel}
                </Button>
              </DialogClose>
              <Button
                onClick={handleCreateSubmit}
                disabled={!canCreateTemplate}
              >
                {createSubmitting && <Loader2 className="animate-spin" />}
                {t.trafficTemplates.dialog.create}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t.trafficTemplates.dialog.editTitle}</DialogTitle>
              <DialogDescription>
                {t.trafficTemplates.dialog.editDescription}
              </DialogDescription>
            </DialogHeader>

            {editInlineError && (
              <p className="text-sm text-destructive whitespace-pre-line">
                {editInlineError}
              </p>
            )}

            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {t.trafficTemplates.key}
                </label>
                <Input value={editTarget?.key ?? ''} disabled />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="edit-template-description"
                  className="text-sm font-medium"
                >
                  {t.trafficTemplates.description}
                </label>
                <Textarea
                  id="edit-template-description"
                  value={editDescription}
                  placeholder={t.trafficTemplates.descriptionPlaceholder}
                  onChange={(event) => setEditDescription(event.target.value)}
                  disabled={editSubmitting}
                />
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium tracking-wide">
                  {t.trafficTemplates.replaceFileSectionTitle}
                </p>
                <div className="flex items-center gap-3">
                  <Button
                    id="edit-template-file"
                    type="button"
                    variant="outline"
                    className="border"
                    onClick={() => editFileInputRef.current?.click()}
                    disabled={editSubmitting}
                  >
                    {t.trafficTemplates.chooseNativeFile}
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {editFile?.name ?? t.trafficTemplates.noFileChosen}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {t.trafficTemplates.oneFileOnly}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t.trafficTemplates.allowedTypesCsv}
                </p>
              </div>
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button
                  variant="outline"
                  onClick={() => {
                    setEditDialogOpen(false);
                    setEditTarget(null);
                    setEditFile(null);
                    setEditInlineError(null);
                  }}
                  disabled={editSubmitting}
                >
                  {t.common.cancel}
                </Button>
              </DialogClose>
              <Button onClick={handleEditSubmit} disabled={!canUpdateTemplate}>
                {editSubmitting && <Loader2 className="animate-spin" />}
                {t.trafficTemplates.dialog.update}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t.trafficTemplates.dialog.deleteTitle}</DialogTitle>
              <DialogDescription>
                {`${t.trafficTemplates.dialog.deleteDescriptionPrefix} "${deleteTarget?.key ?? ''}". ${t.trafficTemplates.dialog.deleteDescriptionSuffix}`}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button
                  variant="outline"
                  onClick={() => {
                    setDeleteDialogOpen(false);
                    setDeleteTarget(null);
                  }}
                  disabled={deleteSubmitting}
                >
                  {t.common.cancel}
                </Button>
              </DialogClose>
              <Button
                variant="destructive"
                onClick={handleDeleteSubmit}
                disabled={deleteSubmitting}
              >
                {deleteSubmitting && <Loader2 className="animate-spin" />}
                {t.trafficTemplates.dialog.delete}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Page>
  );
}
