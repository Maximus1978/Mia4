# ChatGPT Design App

## Overview

The ChatGPT Design App is a user-friendly interface that allows users to interact with AI models through a chat interface. The application features a collapsible left panel for easy navigation, a diary for notes, project folders for organization, and various settings for customization.

## Features

- **Collapsible Left Panel**: Contains sections for sessions, diary, project folders, and settings.
- **Model Selection**: Users can choose from different AI models.
- **User Queries**: Input window styled with accent colors for user queries.
- **AI Responses**: Responses from the AI are styled with Mia's icon for easy identification.
- **Feedback Mechanism**: Like and dislike buttons for user feedback on AI responses.
- **Input Window**: Includes placeholder icons for adding files, sending voice messages, and initiating voice chat.

## Project Structure

```
chatgpt-design-app
├── public
│   └── index.html
├── src
│   ├── main.tsx
│   ├── App.tsx
│   ├── styles
│   │   ├── globals.css
│   │   └── theme.css
│   ├── components
│   │   ├── LeftPanel
│   │   │   ├── LeftPanel.tsx
│   │   │   ├── SessionsList.tsx
│   │   │   ├── Diary.tsx
│   │   │   ├── ProjectFolders.tsx
│   │   │   ├── SettingsIcon.tsx
│   │   │   └── ModelSelector.tsx
│   │   ├── Chat
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── UserMessage.tsx
│   │   │   ├── AIMessage.tsx
│   │   │   ├── FeedbackButtons.tsx
│   │   │   ├── InputBar.tsx
│   │   │   └── Icons
│   │   │       ├── AddFileIcon.tsx
│   │   │       ├── VoiceMessageIcon.tsx
│   │   │       ├── VoiceChatIcon.tsx
│   │   │       └── MiaIcon.tsx
│   ├── context
│   │   ├── SessionContext.tsx
│   │   └── ThemeContext.tsx
│   ├── hooks
│   │   ├── useAccentColor.ts
│   │   └── useModelSelection.ts
│   ├── utils
│   │   ├── messageFormatting.ts
│   │   └── storage.ts
│   ├── data
│   │   └── initialSessions.json
│   └── types
│       └── index.ts
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd chatgpt-design-app
   ```
3. Install dependencies:
   ```
   npm install
   ```

## Usage

To start the application, run:
```
npm run dev
```
Open your browser and navigate to `http://localhost:3000` to view the app.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.