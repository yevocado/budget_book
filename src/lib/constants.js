export const EXPENSE_CATEGORIES = [
  { id: 'food', label: '식비', icon: '🍽️', color: '#FF6B6B' },
  { id: 'transport', label: '교통', icon: '🚌', color: '#4ECDC4' },
  { id: 'shopping', label: '쇼핑', icon: '🛍️', color: '#45B7D1' },
  { id: 'culture', label: '문화/여가', icon: '🎬', color: '#96CEB4' },
  { id: 'health', label: '의료/건강', icon: '💊', color: '#FFEAA7' },
  { id: 'housing', label: '주거/공과금', icon: '🏠', color: '#DDA0DD' },
  { id: 'date', label: '데이트', icon: '💑', color: '#FFB6C1' },
  { id: 'etc', label: '기타', icon: '📦', color: '#C0C0C0' },
]

export const INCOME_CATEGORIES = [
  { id: 'salary', label: '급여', icon: '💰', color: '#51CF66' },
  { id: 'extra', label: '부수입', icon: '💵', color: '#339AF0' },
  { id: 'gift', label: '용돈/선물', icon: '🎁', color: '#FF8CC8' },
  { id: 'etc', label: '기타', icon: '📦', color: '#C0C0C0' },
]

export const ALL_CATEGORIES = [...INCOME_CATEGORIES, ...EXPENSE_CATEGORIES]
