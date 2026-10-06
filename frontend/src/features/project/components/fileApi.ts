import { api } from "@/lib/api";
import { toast } from "@/lib/toast";
import type { FileContent, FileOut } from "@/lib/types";
import { errMsg } from "./format";

export function loadContent(f: FileOut): Promise<FileContent> {
  return api.get<FileContent>(`/files/${f.id}/content`);
}

export function loadVersions(f: FileOut): Promise<FileOut[]> {
  return api.get<FileOut[]>(`/files/${f.id}/versions`);
}

export function downloadFile(f: FileOut): void {
  api.download(`/files/${f.id}/download`, f.name).catch((e: unknown) => toast.error(errMsg(e)));
}
