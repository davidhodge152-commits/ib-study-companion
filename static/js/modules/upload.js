/**
 * Document upload (drag-drop + file input) and document deletion.
 */

import { api } from './api.js';

// ── Upload (drag-drop + file input) ──────────────────────────────

function initUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-indigo-500', 'bg-indigo-50');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
        const files = e.dataTransfer.files;
        for (const file of files) {
            const name = file.name.toLowerCase();
            if (name.endsWith('.pdf') || name.endsWith('.png') || name.endsWith('.jpg') || name.endsWith('.jpeg')) {
                uploadFile(file);
            }
        }
    });

    // Camera capture button
    const cameraBtn = document.getElementById('camera-btn');
    if (cameraBtn) {
        cameraBtn.addEventListener('click', () => startCameraCapture());
    }

    fileInput.addEventListener('change', () => {
        for (const file of fileInput.files) {
            uploadFile(file);
        }
        fileInput.value = '';
    });

    // Doc-type button selection
    document.querySelectorAll('.doc-type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            window.selectedDocType = btn.dataset.type;
        });
    });
}

function uploadFile(file) {
    const progress = document.getElementById('upload-progress');
    const bar = document.getElementById('upload-bar');
    const filename = document.getElementById('upload-filename');
    const status = document.getElementById('upload-status');
    const result = document.getElementById('upload-result');

    progress.classList.remove('hidden');
    result.classList.add('hidden');
    filename.textContent = file.name;
    status.textContent = 'Uploading...';
    bar.style.width = '30%';

    const formData = new FormData();
    formData.append('file', file);
    const selectedDocType = typeof window.selectedDocType !== 'undefined'
        ? window.selectedDocType
        : (document.querySelector('.doc-type-btn.active')?.dataset?.type || 'notes');
    formData.append('doc_type', selectedDocType);

    api.postForm('/api/upload', formData)
        .then(res => {
            bar.style.width = '80%';
            status.textContent = 'Processing...';
            return res.json();
        })
        .then(data => {
            bar.style.width = '100%';
            if (data.error) {
                status.textContent = 'Failed';
                bar.classList.remove('bg-indigo-600');
                bar.classList.add('bg-red-500');
                result.innerHTML = `<div class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">${data.error}</div>`;
            } else {
                status.textContent = 'Done!';
                result.innerHTML = `
                    <div class="p-4 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm">
                        <strong>${data.filename}</strong> uploaded and indexed successfully.
                        <br><span class="text-green-600">${data.chunks} chunks | ${data.doc_type.replace(/_/g, ' ')} | ${data.subject.replace(/_/g, ' ')}</span>
                    </div>`;
                setTimeout(() => location.reload(), 1500);
            }
            result.classList.remove('hidden');
        })
        .catch(err => {
            bar.style.width = '100%';
            bar.classList.remove('bg-indigo-600');
            bar.classList.add('bg-red-500');
            status.textContent = 'Error';
            result.innerHTML = `<div class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">Upload failed: ${err.message}</div>`;
            result.classList.remove('hidden');
        });
}

// ── Document deletion ────────────────────────────────────────────

export function deleteDocument(docId) {
    if (!confirm('Delete this document? This will remove it from the knowledge base.')) return;

    api.delete(`/api/documents/${docId}`)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const row = document.getElementById(`doc-${docId}`);
                if (row) row.remove();
            } else {
                alert(data.error || 'Failed to delete document.');
            }
        })
        .catch(err => alert('Error: ' + err.message));
}

// ── Camera capture ──────────────────────────────────────────────
function startCameraCapture() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Camera access is not supported on this device.');
        return;
    }

    // Create a modal with video preview
    const modal = document.createElement('div');
    modal.id = 'camera-modal';
    modal.className = 'fixed inset-0 bg-black/80 z-50 flex flex-col items-center justify-center p-4';
    modal.innerHTML = `
        <video id="camera-preview" autoplay playsinline class="max-w-full max-h-[60vh] rounded-xl"></video>
        <div class="flex gap-3 mt-4">
            <button id="camera-capture" class="px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium">Capture</button>
            <button id="camera-close" class="px-6 py-3 bg-slate-600 text-white rounded-xl font-medium">Cancel</button>
        </div>
        <canvas id="camera-canvas" class="hidden"></canvas>
    `;
    document.body.appendChild(modal);

    const video = document.getElementById('camera-preview');
    const canvas = document.getElementById('camera-canvas');

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(stream => {
            video.srcObject = stream;

            document.getElementById('camera-capture').onclick = () => {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                canvas.toBlob(blob => {
                    stream.getTracks().forEach(t => t.stop());
                    modal.remove();
                    const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
                    uploadFile(file);
                }, 'image/jpeg', 0.9);
            };

            document.getElementById('camera-close').onclick = () => {
                stream.getTracks().forEach(t => t.stop());
                modal.remove();
            };
        })
        .catch(() => {
            modal.remove();
            alert('Unable to access camera. Please check permissions.');
        });
}

// Auto-init on import (modules are deferred, DOM is ready)
initUpload();
