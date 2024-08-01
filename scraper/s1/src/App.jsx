import React, { useState, useRef, useEffect } from 'react';
import './App.css';
import SampleTable from './Sampledata';
import FormComponent from './directurls';
import Select from 'react-select';

import io from 'socket.io-client';

const socket = io('http://localhost:5000');

const options = [
  { value: 'gpt-3.5-turbo', label: 'gpt-3.5-turbo ' },
  { value: 'gpt-4o', label: 'gpt-4o' },
  { value: 'gpt-4o-mini', label: 'gpt-4o-mini' },
  { value: '', label: 'none' },
];
const openai_options = [
  { value: 'gpt-3.5-turbo', label: 'gpt-3.5-turbo ' },
  { value: 'gpt-4o', label: 'gpt-4o' },
  { value: 'gpt-4o-mini', label: 'gpt-4o-mini' },
  { value: '', label: 'none' },
];

const customStyles = {
  control: (provided, state) => ({
    ...provided,
    borderColor: state.isFocused ? '#007bff' : provided.borderColor,
    boxShadow: state.isFocused ? '0 0 0 1px #007bff' : provided.boxShadow,
    '&:hover': {
      borderColor: state.isFocused ? '#007bff' : provided.borderColor,
    },
  }),
};

function App() {
  const [scrap, setScrap] = useState('Click on the button for sample output');
  const [fullscrap, setfullScrap] = useState('Click on the button for output file to download');
  const [upload, setUpload] = useState('File not found');
  const [textPrompt, setTextPrompt] = useState('');
  const [textPrompt_openai, setTextPrompt_openai] = useState('');
  const fileInputRef = useRef(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [openaiselectedOption, setopenaiSelectedOption] = useState(null);
  const [model, setmodel] = useState('');
  const [openaimodel, setopenaimodel] = useState('');
  const [file_name, setfile_name] = useState('');
  const [email, setEmail] = useState('');
  const [formData, setFormData] = useState({
    url1: '',
    url2: '',
    url3: ''
  });

  const handleEmailChange = (e) => {
    setEmail(e.target.value);
  };

  const handleUrlChange = (e) => {
    const { id, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [id]: value
    }));
  };

  const handleChange = (selectedOption) => {
    setSelectedOption(selectedOption);
    setmodel(selectedOption.value);
  };

  const handle_openai_model_Change = (openaiselectedOption) => {
    setopenaiSelectedOption(openaiselectedOption);
    setopenaimodel(openaiselectedOption.value);
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'text/csv') {
      setUpload(`Uploading ${file.name} file .....`);
      setfile_name(file.name);
      const formData = new FormData();
      formData.append('file', file);
      try {
        const response = await fetch('http://localhost:5000/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        const data = await response.json();

        if (data.message === 'File successfully uploaded') {
          setUpload('File uploaded successfully!');
        } else {
          setUpload('Failed to upload file.');
        }
        // Reset file input field
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } catch (error) {
        setUpload('Failed to upload file.');
        console.error('There was an error uploading the file!', error);
      }
    } else {
      alert('Please upload a valid CSV file.');
    }
  };

  const [data, setData] = useState([]);



  const sampleUrls = async () => {
    if (!file_name && (!formData.url1 && !formData.url2 && !formData.url3)) {
      alert('Please upload a CSV file or provide at least one URL');
      return;
    }

    setScrap("Processing the URLs...");

    // Extract URLs from formData
    const { url1, url2, url3 } = formData;

    const queryParams = new URLSearchParams({
      url1: url1,
      url2: url2,
      url3: url3,
      textPrompt,
      model,
      textPrompt_openai,
      openaimodel,
      file_name
    }).toString();

    try {
      const response = await fetch(`http://localhost:5000/urls?${queryParams}`);
      const res_data = await response.json();

      if (res_data.urls && res_data.urls.length > 0) {
        if (res_data.urls[0].title === "no such column") {
          setScrap('Change the URLs column name to Website');
        } else if (Array.isArray(res_data.urls)) {
          setData(res_data.urls);
          setScrap('');
        } else {
          setScrap('Prompt or model field is required');
        }
      } else {
        setScrap('No URLs found or URL list is empty');
      }

    } catch (error) {
      console.error('Error fetching or parsing data:', error);
      setScrap('Error fetching or parsing data...');
    }
  };



  const [value, setValue] = useState("");

  useEffect(() => {
    socket.on('value_update', (data) => {
      setValue(data.value);
    });

    return () => {
      socket.off('value_update');
    };
  }, []);

  const runFullUrls = async () => {
    if (!file_name) {
      alert('Please upload a CSV file first');
      return;
    }
    if (!email) {
      alert('Please enter an email');
      return;
    }
    setfullScrap("processing the Urls........")
    try {
      const response = await fetch(`http://localhost:5000/fullurls?textPrompt=${textPrompt}&model=${model}&textPrompt_openai=${textPrompt_openai}&openaimodel=${openaimodel}&email=${email}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'data.csv');
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      setfullScrap('scraping of websites completed successfully check it in your chrome download and also mailed to your gmail');
    } catch (error) {
      setfullScrap('Failed to scrape websites');
      console.error('Error downloading the CSV file:', error);
    }
  };

  return (
    <div>
      <div className="scrap_urls_container">
        <h1>Evergrow Advisors</h1>
        <h2>Scrape Urls</h2>
        <FormComponent formData={formData} handleUrlChange={handleUrlChange} />
        <p><b>Note</b>: urls column name should be "Website"</p>
        <div>
          <input type="file" accept=".csv" ref={fileInputRef} onChange={handleFileChange} />
          <p>{upload}</p>
        </div>
        <div className='prompt'>
          <label htmlFor="promptTextarea">Prompt 1(mandatory):</label>
          <textarea id="promptTextarea" rows="4" cols="50" onChange={(e) => setTextPrompt(e.target.value)}></textarea>
        </div>

        <h4>Select Openai LLM model</h4>

        <div className="dropdown-container">
          <Select value={selectedOption} onChange={handleChange} options={options} styles={customStyles} classNamePrefix="react-select" />
          {selectedOption && <p className="selected-option">selected LLM model: <b>{selectedOption.value}</b></p>}
        </div>

        <div className='prompt'>
          <label htmlFor="promptTextarea">Prompt 2(optional-through openai model):</label>
          <textarea id="promptTextarea" rows="4" cols="50" onChange={(e) => setTextPrompt_openai(e.target.value)}></textarea>
        </div>
        <h4>Select OpenAI LLM model</h4>
        <div className="dropdown-container">
          <Select value={openaiselectedOption} onChange={handle_openai_model_Change} options={openai_options} styles={customStyles} classNamePrefix="react-select" />
          {openaiselectedOption && <p className="selected-option">selected LLM model: <b>{openaiselectedOption.value}</b></p>}
        </div>

        <div className='website'>
          <button type="button" className="btn btn-primary btn-sm" onClick={sampleUrls}>Run 5 sample websites</button>
          <p>{scrap}</p>
        </div>
        <SampleTable data={data} openaimodel={openaimodel} />

        <div className="form-email-group">
          <label htmlFor="email" className="form-label">Email</label>
          <input
            type="email"
            id="email"
            required
            className="form-input"
            value={email}
            onChange={handleEmailChange}
          />
        </div>
        <div className='website'>
          <button type="button" className="btn btn-primary btn-sm" onClick={runFullUrls}>Run Full CSV File</button>
          <p>{fullscrap}</p>
          <p>{value}</p>
        </div>
      </div>
    </div>
  );
}

export default App;
