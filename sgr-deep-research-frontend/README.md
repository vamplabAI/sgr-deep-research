# SGR Deep Research Frontend

## 🚀 Quick Start

### Prerequisites

- Node.js 20.19+ or 22.12+

### Setup

1. **Install Node.js 22** (macOS):

```sh
brew install node@22
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
```

2. **Install dependencies**:

```sh
npm install
```

3. **Configure environment**:

```sh
cp .env.example .env.local
```

Edit `.env.local` and set:

- `VITE_API_BASE_URL` - your backend URL (default: `http://localhost:8010`)

### Run

**Development:**

```sh
npm run dev
```

Open http://localhost:5173
