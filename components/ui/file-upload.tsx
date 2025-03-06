import { Upload } from "lucide-react";
import { ChangeEvent, DragEvent, useState } from "react";
import { Button } from "./button";

interface FileUploadProps {
  onFileSelect: (file: File | null) => void;
  maxFileSize?: number;
  fileType?: string;
  uploadButtonLabel?: string;
  dragDropText?: string;
  isUploading?: boolean;
  onUpload?: () => void;
  selectedFile: File | null;
}

export function FileUpload({
  onFileSelect,
  maxFileSize = 10 * 1024 * 1024, // 10MB default
  fileType = ".pdf",
  uploadButtonLabel = "Upload File",
  dragDropText = "Drag and drop your file here, or click to select",
  isUploading = false,
  onUpload,
  selectedFile,
}: Readonly<FileUploadProps>) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      if (files[0].size > maxFileSize) {
        alert("File size exceeds 10MB limit");
        return;
      }
      onFileSelect(files[0]);
    }
  };

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      if (selectedFile.size > maxFileSize) {
        alert("File size exceeds 10MB limit");
        return;
      }
      onFileSelect(selectedFile);
    }
  };

  const removeFile = (e: React.MouseEvent) => {
    e.preventDefault();
    onFileSelect(null);
  };

  return (
    <div className="w-full max-w-xl px-4">
      <div
        className={`relative w-full rounded-lg border-2 border-dashed transition-all duration-200 ${
          isDragging
            ? "border-white bg-white/20"
            : "border-blue-600 bg-white/10 hover:border-white hover:bg-white/10 hover:shadow-lg hover:scale-[1.01]"
        } backdrop-blur-sm p-8 group`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <input
          type="file"
          className="hidden"
          id="file-upload"
          onChange={handleFileInput}
          accept={fileType}
        />

        <label
          htmlFor="file-upload"
          className="flex flex-col items-center justify-center cursor-pointer"
        >
          {!selectedFile ? (
            <>
              <Upload className="w-12 h-12 text-white mb-4 transition-transform duration-200 group-hover:scale-110" />
              <p className="text-white text-center mb-2 transition-all duration-200 group-hover:transform group-hover:translate-y-1">
                {dragDropText}
              </p>
              <p className="text-white/70 text-sm text-center transition-opacity duration-200 group-hover:text-white">
                Supported Formats: PDF (Max Size: 10MB / Max Pages: 2)
              </p>
            </>
          ) : (
            <div className="flex flex-col items-center">
              <p className="text-white mb-2">Selected file:</p>
              <p className="text-white font-medium mb-4">{selectedFile.name}</p>
              <button
                onClick={removeFile}
                className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-white transition-all duration-200"
              >
                Remove
              </button>
            </div>
          )}
        </label>
      </div>
      {selectedFile && onUpload && (
        <Button
          className="mt-6 w-full bg-white text-blue-600 font-semibold rounded-full hover:shadow-xl transition-all duration-300 hover:scale-105"
          size="lg"
          onClick={onUpload}
          disabled={isUploading}
        >
          {isUploading ? "Uploading…" : uploadButtonLabel}
        </Button>
      )}
    </div>
  );
}
