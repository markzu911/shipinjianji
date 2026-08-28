(() => {
  "use strict";

  const DATABASE_NAME = "video-editor-timeline-thumbnails";
  const DATABASE_VERSION = 1;
  const STORE_NAME = "timeline-thumbnails";
  const DEFAULT_CACHE_VERSION = 1;
  const DEFAULT_MAX_RECORDS = 24;
  const DEFAULT_MAX_BYTES = 64 * 1024 * 1024;
  const DEFAULT_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;

  function cacheError(message) {
    return new Error(`Timeline thumbnail cache: ${message}`);
  }

  function positiveLimit(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? number : fallback;
  }

  function safeWindowValue(key) {
    try {
      return window[key];
    } catch (_error) {
      return null;
    }
  }

  function validBlob(blob, BlobType) {
    return (
      typeof BlobType === "function" &&
      blob instanceof BlobType &&
      blob.size > 0 &&
      blob.type === "image/jpeg"
    );
  }

  function normalizeRecord(record, cacheVersion, BlobType) {
    if (!record || typeof record !== "object") return null;
    if (typeof record.signature !== "string" || !record.signature) return null;
    if (record.cacheVersion !== cacheVersion) return null;
    if (typeof record.jobId !== "string") return null;
    if (!Number.isFinite(record.sourceDuration) || record.sourceDuration <= 0) {
      return null;
    }
    if (!Number.isInteger(record.count) || record.count <= 0) return null;
    if (!Array.isArray(record.frames) || record.frames.length !== record.count) {
      return null;
    }

    let previousSourceTime = Number.NEGATIVE_INFINITY;
    let byteSize = 0;
    const frames = [];
    for (const frame of record.frames) {
      const sourceTime = Number(frame?.sourceTime);
      if (
        !Number.isFinite(sourceTime) ||
        sourceTime < 0 ||
        sourceTime + 0.001 < previousSourceTime ||
        sourceTime > record.sourceDuration + 0.05 ||
        !validBlob(frame?.blob, BlobType)
      ) {
        return null;
      }
      previousSourceTime = sourceTime;
      byteSize += frame.blob.size;
      frames.push({ blob: frame.blob, sourceTime });
    }

    const createdAt = Number(record.createdAt);
    const lastAccessedAt = Number(record.lastAccessedAt);
    if (
      !Number.isFinite(createdAt) ||
      createdAt <= 0 ||
      !Number.isFinite(lastAccessedAt) ||
      lastAccessedAt <= 0 ||
      Number(record.byteSize) !== byteSize
    ) {
      return null;
    }

    return {
      byteSize,
      cacheVersion,
      count: record.count,
      createdAt,
      frames,
      jobId: record.jobId,
      lastAccessedAt,
      signature: record.signature,
      sourceDuration: record.sourceDuration,
    };
  }

  function createStore(options = {}) {
    const indexedDb = options.indexedDB ?? safeWindowValue("indexedDB");
    const BlobType = options.Blob ?? safeWindowValue("Blob");
    const databaseName = options.databaseName || DATABASE_NAME;
    const cacheVersion = Math.max(
      1,
      Math.floor(positiveLimit(options.cacheVersion, DEFAULT_CACHE_VERSION)),
    );
    const maxRecords = Math.max(
      1,
      Math.floor(positiveLimit(options.maxRecords, DEFAULT_MAX_RECORDS)),
    );
    const maxBytes = positiveLimit(options.maxBytes, DEFAULT_MAX_BYTES);
    const maxAgeMs = positiveLimit(options.maxAgeMs, DEFAULT_MAX_AGE_MS);
    const now = typeof options.now === "function" ? options.now : Date.now;
    let connection = null;
    let opening = null;
    let closed = false;

    function openDatabase() {
      if (closed) return Promise.reject(cacheError("store is closed"));
      if (!indexedDb?.open) {
        return Promise.reject(cacheError("IndexedDB is unavailable"));
      }
      if (connection) return Promise.resolve(connection);
      if (opening) return opening;

      let request;
      try {
        request = indexedDb.open(databaseName, DATABASE_VERSION);
      } catch (error) {
        return Promise.reject(error);
      }
      opening = new Promise((resolve, reject) => {
        let settled = false;

        const fail = (error) => {
          if (settled) return;
          settled = true;
          opening = null;
          reject(error || cacheError("database open failed"));
        };
        request.onupgradeneeded = () => {
          const database = request.result;
          if (!database.objectStoreNames.contains(STORE_NAME)) {
            database.createObjectStore(STORE_NAME, { keyPath: "signature" });
          }
        };
        request.onerror = () => fail(request.error);
        request.onblocked = () => fail(cacheError("database open blocked"));
        request.onsuccess = () => {
          const database = request.result;
          if (settled || closed) {
            database.close();
            if (!settled) fail(cacheError("store is closed"));
            return;
          }
          settled = true;
          opening = null;
          connection = database;
          database.onversionchange = () => {
            database.close();
            if (connection === database) connection = null;
          };
          resolve(database);
        };
      });
      return opening;
    }

    function load(signature) {
      if (typeof signature !== "string" || !signature) {
        return Promise.resolve(null);
      }
      return openDatabase().then(
        (database) =>
          new Promise((resolve, reject) => {
            let result = null;
            let settled = false;
            let transaction;
            try {
              transaction = database.transaction(STORE_NAME, "readwrite");
              const store = transaction.objectStore(STORE_NAME);
              const request = store.get(signature);
              request.onsuccess = () => {
                const record = normalizeRecord(
                  request.result,
                  cacheVersion,
                  BlobType,
                );
                if (!record) {
                  if (request.result !== undefined) store.delete(signature);
                  return;
                }
                record.lastAccessedAt = Number(now());
                if (!Number.isFinite(record.lastAccessedAt)) {
                  record.lastAccessedAt = Date.now();
                }
                store.put(record);
                result = record;
              };
            } catch (error) {
              reject(error);
              return;
            }
            transaction.oncomplete = () => {
              if (settled) return;
              settled = true;
              resolve(result);
            };
            transaction.onerror = () => {
              if (settled) return;
              settled = true;
              reject(transaction.error || cacheError("load failed"));
            };
            transaction.onabort = transaction.onerror;
          }),
      );
    }

    function save(record) {
      const normalized = normalizeRecord(record, cacheVersion, BlobType);
      if (!normalized) return Promise.reject(cacheError("invalid record"));
      return openDatabase()
        .then(
          (database) =>
            new Promise((resolve, reject) => {
              let settled = false;
              let transaction;
              try {
                transaction = database.transaction(STORE_NAME, "readwrite");
                transaction.objectStore(STORE_NAME).put(normalized);
              } catch (error) {
                reject(error);
                return;
              }
              transaction.oncomplete = () => {
                if (settled) return;
                settled = true;
                resolve();
              };
              transaction.onerror = () => {
                if (settled) return;
                settled = true;
                reject(transaction.error || cacheError("save failed"));
              };
              transaction.onabort = transaction.onerror;
            }),
        )
        .then(() => {
          Promise.resolve()
            .then(() => prune({ preserveSignature: normalized.signature }))
            .catch(() => {});
        });
    }

    function prune({ preserveSignature = "" } = {}) {
      return openDatabase().then(
        (database) =>
          new Promise((resolve, reject) => {
            let removed = 0;
            let settled = false;
            let transaction;
            try {
              transaction = database.transaction(STORE_NAME, "readwrite");
              const store = transaction.objectStore(STORE_NAME);
              const request = store.getAll();
              request.onsuccess = () => {
                const currentTime = Number(now());
                const timestamp = Number.isFinite(currentTime)
                  ? currentTime
                  : Date.now();
                const records = [];
                for (const candidate of request.result || []) {
                  const record = normalizeRecord(
                    candidate,
                    cacheVersion,
                    BlobType,
                  );
                  if (!record) {
                    if (typeof candidate?.signature === "string") {
                      store.delete(candidate.signature);
                      removed += 1;
                    }
                    continue;
                  }
                  records.push(record);
                }
                records.sort((left, right) => {
                  if (left.signature === preserveSignature) return -1;
                  if (right.signature === preserveSignature) return 1;
                  return right.lastAccessedAt - left.lastAccessedAt;
                });

                let keptRecords = 0;
                let keptBytes = 0;
                for (const record of records) {
                  const preserved = record.signature === preserveSignature;
                  const expired = timestamp - record.lastAccessedAt > maxAgeMs;
                  const exceedsCount = keptRecords >= maxRecords;
                  const exceedsBytes = keptBytes + record.byteSize > maxBytes;
                  if (!preserved && (expired || exceedsCount || exceedsBytes)) {
                    store.delete(record.signature);
                    removed += 1;
                    continue;
                  }
                  keptRecords += 1;
                  keptBytes += record.byteSize;
                }
              };
            } catch (error) {
              reject(error);
              return;
            }
            transaction.oncomplete = () => {
              if (settled) return;
              settled = true;
              resolve(removed);
            };
            transaction.onerror = () => {
              if (settled) return;
              settled = true;
              reject(transaction.error || cacheError("prune failed"));
            };
            transaction.onabort = transaction.onerror;
          }),
      );
    }

    function close() {
      if (closed) return;
      closed = true;
      connection?.close();
      connection = null;
    }

    return Object.freeze({ close, load, prune, save });
  }

  window.TimelineThumbnailCache = Object.freeze({
    CACHE_VERSION: DEFAULT_CACHE_VERSION,
    createStore,
  });
})();
