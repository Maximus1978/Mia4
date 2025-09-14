import React, { useState } from 'react';
import AddFileIcon from './Icons/AddFileIcon';
import VoiceMessageIcon from './Icons/VoiceMessageIcon';
import VoiceChatIcon from './Icons/VoiceChatIcon';

interface Props { onSendMessage: (text: string) => void; disabled?: boolean }

const InputBar: React.FC<Props> = ({ onSendMessage, disabled = false }) => {
    const [inputValue, setInputValue] = useState('');

    const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        setInputValue(event.target.value);
    };

    const handleSendMessage = () => {
        const text = inputValue.trim();
        if (!text) return;
        onSendMessage(text);
        setInputValue('');
    };

    return (
        <div className="input-bar">
            <div className="input-icons">
                <AddFileIcon />
                <VoiceMessageIcon />
                <VoiceChatIcon />
            </div>
            <input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                placeholder="Type your message..."
                className="input-field"
                disabled={disabled}
            />
            <button onClick={handleSendMessage} className="send-button" disabled={disabled}>
                Send
            </button>
        </div>
    );
};

export default InputBar;