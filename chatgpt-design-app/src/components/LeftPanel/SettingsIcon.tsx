import React from 'react';

interface Props { onClick: () => void }

const SettingsIcon: React.FC<Props> = ({ onClick }) => {
    return (
        <button className="settings-icon" onClick={onClick} title="Settings">
            ⚙️ Settings
        </button>
    );
};

export default SettingsIcon;