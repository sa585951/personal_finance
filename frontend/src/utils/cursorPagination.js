export function createCursorPager(pageSize = 20) {
  return {
    page: 1,
    pageSize,
    cursors: [null],
  };
}

export function resetCursorPager(pager) {
  return createCursorPager(pager?.pageSize || 20);
}

export function cursorForPage(pager, page) {
  if (!pager || page < 1) return null;
  return pager.cursors[page - 1] || null;
}

export function recordCursorPage(pager, page, cursor) {
  const nextPager = {
    page,
    pageSize: pager?.pageSize || 20,
    cursors: [...(pager?.cursors || [null])],
  };
  if (page === 1) {
    nextPager.cursors = [null];
  } else {
    nextPager.cursors[page - 1] = cursor || null;
    nextPager.cursors = nextPager.cursors.slice(0, page);
  }
  return nextPager;
}
