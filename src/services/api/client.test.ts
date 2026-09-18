import { describe, it, expect } from 'vitest';
import { getStaticFileUrl } from './client';

describe('getStaticFileUrl', () => {
  it('returns empty string for falsy path', () => {
    expect(getStaticFileUrl(undefined)).toBe('');
    expect(getStaticFileUrl('')).toBe('');
  });

  it('preserves full URLs, blob and data URLs', () => {
    expect(getStaticFileUrl('http://example.com/model.stl')).toBe('http://example.com/model.stl');
    expect(getStaticFileUrl('https://example.com/model.stl')).toBe('https://example.com/model.stl');
    expect(getStaticFileUrl('blob:http://localhost:5173/abc')).toBe('blob:http://localhost:5173/abc');
    expect(getStaticFileUrl('data:model/stl;base64,...')).toBe('data:model/stl;base64,...');
  });

  it('correctly builds static URL for user-scoped storage/outputs path', () => {
    const input = 'storage/outputs/users/user_abc/projects/proj_123/model.stl';
    expect(getStaticFileUrl(input)).toBe(
      'http://127.0.0.1:8000/static/outputs/users/user_abc/projects/proj_123/model.stl'
    );
  });

  it('correctly builds static URL with leading slash', () => {
    const input = '/storage/outputs/users/user_abc/projects/proj_123/model.stl';
    expect(getStaticFileUrl(input)).toBe(
      'http://127.0.0.1:8000/static/outputs/users/user_abc/projects/proj_123/model.stl'
    );
  });

  it('correctly builds static URL for storage/uploads path', () => {
    const input = 'storage/uploads/users/user_abc/projects/proj_123/image.png';
    expect(getStaticFileUrl(input)).toBe(
      'http://127.0.0.1:8000/static/uploads/users/user_abc/projects/proj_123/image.png'
    );
  });

  it('falls back to files download endpoint for other paths', () => {
    const input = 'custom/path/model.stl';
    expect(getStaticFileUrl(input)).toBe(
      'http://127.0.0.1:8000/api/v1/files/download?file_path=custom%2Fpath%2Fmodel.stl'
    );
  });
});
