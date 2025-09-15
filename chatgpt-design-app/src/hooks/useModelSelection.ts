import { useState } from 'react';

const models = [
    { id: 'gpt-3.5', name: 'GPT-3.5' },
    { id: 'gpt-4', name: 'GPT-4' },
    { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' },
];

const useModelSelection = () => {
    const [selectedModel, setSelectedModel] = useState(models[0].id);

    const selectModel = (modelId: string) => {
        if (models.some(model => model.id === modelId)) {
            setSelectedModel(modelId);
        }
    };

    return {
        selectedModel,
        selectModel,
        models,
    };
};

export default useModelSelection;