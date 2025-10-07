# Шпаргалка частых задач для AI

## Как добавить новое поле в форму

### 1. Добавить в Zod схему
```typescript
// В types/strategy.ts
export interface StrategyParams {
  // ... существующие поля
  newField?: string;  // Новое поле
}

// В компоненте с формой
const schema = z.object({
  // ... существующие поля
  newField: z.string().optional(),
});
```

### 2. Добавить в React Hook Form
```typescript
const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: zodResolver(schema),
});

// В JSX
<input
  {...register("newField")}
  className="w-full px-3 py-2 border rounded-md"
  placeholder="Новое поле"
/>
{errors.newField && <span className="text-red-500">{errors.newField.message}</span>}
```

### 3. Обновить Zustand store
```typescript
// В store/strategy.ts
setField: <K extends keyof StrategyParams>(field: K, value: StrategyParams[K]) => {
  set({
    current: {
      ...get().current,
      [field]: value
    }
  });
},
```

## Как добавить новый API endpoint

### 1. Создать типы
```typescript
// В types/new-feature.ts
export interface NewFeatureRequest {
  field1: string;
  field2: number;
}

export interface NewFeatureResponse {
  id: string;
  result: string;
}
```

### 2. Добавить в API клиент
```typescript
// В lib/api-new-feature.ts
export class NewFeatureAPI {
  static async createFeature(data: NewFeatureRequest): Promise<NewFeatureResponse> {
    const response = await fetch(`${BASE_URL}/new-feature`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }
}
```

### 3. Использовать в компоненте
```typescript
const handleSubmit = async (data: NewFeatureRequest) => {
  try {
    const result = await NewFeatureAPI.createFeature(data);
    console.log('Success:', result);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

## Как изменить Zustand store

### Добавить новое поле
```typescript
// В store/example.ts
interface ExampleState {
  // ... существующие поля
  newField: string;
  setNewField: (value: string) => void;
}

export const useExampleStore = create<ExampleState>()(
  persist(
    (set) => ({
      // ... существующие поля
      newField: '',
      setNewField: (value: string) => set({ newField: value }),
    }),
    {
      name: 'example-storage',
      partialize: (state) => ({
        // ... существующие поля
        newField: state.newField,
      }),
    }
  )
);
```

### Добавить асинхронное действие
```typescript
// В store/example.ts
interface ExampleState {
  loading: boolean;
  fetchData: () => Promise<void>;
}

export const useExampleStore = create<ExampleState>()(
  persist(
    (set, get) => ({
      loading: false,
      fetchData: async () => {
        set({ loading: true });
        try {
          const data = await SomeAPI.getData();
          set({ data, loading: false });
        } catch (error) {
          set({ loading: false });
          throw error;
        }
      },
    }),
    // ... persist config
  )
);
```

## Как добавить новую страницу

### 1. Создать компонент страницы
```typescript
// В pages/NewPage.tsx
import React from 'react';

export default function NewPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Новая страница</h1>
      {/* Контент страницы */}
    </div>
  );
}
```

### 2. Добавить роут
```typescript
// В App.tsx или router файле
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import NewPage from './pages/NewPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ... существующие роуты */}
        <Route path="/new-page" element={<NewPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### 3. Добавить навигацию
```typescript
// В компоненте навигации
<Link to="/new-page" className="nav-link">
  Новая страница
</Link>
```

## Как работать с TypeScript типами

### Создать union type
```typescript
export type Status = 'pending' | 'approved' | 'rejected';
export type UserRole = 'admin' | 'user' | 'guest';
```

### Создать generic interface
```typescript
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

// Использование
const userResponse: ApiResponse<User> = await api.getUser();
```

### Расширить существующий тип
```typescript
// Базовый тип
export interface BaseUser {
  id: string;
  email: string;
}

// Расширенный тип
export interface AdminUser extends BaseUser {
  permissions: string[];
  lastLogin: Date;
}
```

### Создать utility types
```typescript
// Сделать все поля опциональными
export type PartialUser = Partial<User>;

// Выбрать только определенные поля
export type UserSummary = Pick<User, 'id' | 'name' | 'email'>;

// Исключить определенные поля
export type UserWithoutPassword = Omit<User, 'password'>;
```

## Типичные ошибки и решения

### Ошибка: "Property does not exist on type"
```typescript
// ❌ Неправильно
const user = { name: 'John' };
console.log(user.age); // Error: Property 'age' does not exist

// ✅ Правильно
interface User {
  name: string;
  age?: number; // Опциональное поле
}
const user: User = { name: 'John' };
console.log(user.age); // OK, может быть undefined
```

### Ошибка: "Cannot read property of undefined"
```typescript
// ❌ Неправильно
const data = await api.getData();
console.log(data.items.length); // Error если data.items undefined

// ✅ Правильно
const data = await api.getData();
if (data?.items) {
  console.log(data.items.length);
}
```

### Ошибка: "Type is not assignable"
```typescript
// ❌ Неправильно
const status: string = 'pending'; // Error если ожидается Status type

// ✅ Правильно
const status: Status = 'pending';
// или
const status = 'pending' as Status;
```

## Примеры кода для copy-paste

### Debounced input
```typescript
const [query, setQuery] = useState('');
const [debouncedQuery, setDebouncedQuery] = useState('');
const isBlockedRef = useRef(false);

useEffect(() => {
  const timer = setTimeout(() => {
    if (!isBlockedRef.current) {
      setDebouncedQuery(query);
    }
  }, 500);

  return () => clearTimeout(timer);
}, [query]);
```

### Loading state с error handling
```typescript
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);

const handleAction = async () => {
  setLoading(true);
  setError(null);
  
  try {
    await SomeAPI.action();
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Unknown error');
  } finally {
    setLoading(false);
  }
};
```

### Zustand store с API
```typescript
interface DataState {
  items: Item[];
  loading: boolean;
  error: string | null;
  fetchItems: () => Promise<void>;
  addItem: (item: Item) => void;
}

export const useDataStore = create<DataState>()(
  persist(
    (set, get) => ({
      items: [],
      loading: false,
      error: null,
      
      fetchItems: async () => {
        set({ loading: true, error: null });
        try {
          const items = await DataAPI.getItems();
          set({ items, loading: false });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to fetch',
            loading: false 
          });
        }
      },
      
      addItem: (item: Item) => {
        set(state => ({ items: [...state.items, item] }));
      },
    }),
    {
      name: 'data-storage',
      partialize: (state) => ({ items: state.items }),
    }
  )
);
```

### Form с validation
```typescript
const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
  age: z.number().min(18, 'Must be 18+'),
});

type FormData = z.infer<typeof schema>;

const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
  resolver: zodResolver(schema),
});

const onSubmit = (data: FormData) => {
  console.log(data);
};
```

---

**Помни**: Всегда проверяй существующие паттерны в проекте перед созданием новых!


