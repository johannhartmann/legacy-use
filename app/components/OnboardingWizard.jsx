import {
  Close as CloseIcon,
  Key as KeyIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Dialog,
  DialogContent,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAiProvider } from '../contexts/AiProviderContext';
import { getProviders, getTargets, updateProviderSettings } from '../services/apiService';

const OnboardingWizard = ({ open, onClose, onComplete }) => {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const { refreshProviders } = useAiProvider();

  // Provider configuration state
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [awsCredentials, setAwsCredentials] = useState({
    accessKeyId: '',
    secretAccessKey: '',
    region: 'us-east-1',
  });
  const [vertexCredentials, setVertexCredentials] = useState({
    projectId: '',
    region: 'us-central1',
  });

  const steps = ['Welcome', 'Configure Provider'];

  // Fetch providers on component mount and reset state
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const providersData = await getProviders();
        setProviders(providersData.providers || []);

        // Set default provider to Anthropic if available, otherwise first available one
        const anthropicProvider = providersData.providers?.find(p => p.provider === 'anthropic');
        const availableProvider = providersData.providers?.find(p => p.available);
        
        if (anthropicProvider) {
          setSelectedProvider('anthropic');
        } else if (availableProvider) {
          setSelectedProvider(availableProvider.provider);
        } else if (providersData.providers?.length > 0) {
          setSelectedProvider(providersData.providers[0].provider);
        }
      } catch (err) {
        console.error('Error fetching providers:', err);
        setError('Failed to load provider configurations');
      }
    };

    if (open) {
      fetchProviders();
      setError('');
    }
  }, [open]);

  const handleNext = () => {
    setActiveStep(prev => prev + 1);
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  const handleProviderSetup = async () => {
    if (!selectedProvider) {
      setError('Please select a provider');
      return;
    }

    setLoading(true);
    setError('');

    try {
      let credentials = {};

      if (selectedProvider === 'anthropic') {
        if (!apiKeyInput.trim()) {
          setError('Please enter your Anthropic API key');
          return;
        }
        credentials.api_key = apiKeyInput;
      } else if (selectedProvider === 'bedrock') {
        if (!awsCredentials.accessKeyId || !awsCredentials.secretAccessKey) {
          setError('Please enter your AWS credentials');
          return;
        }
        credentials = {
          access_key_id: awsCredentials.accessKeyId,
          secret_access_key: awsCredentials.secretAccessKey,
          region: awsCredentials.region,
        };
      } else if (selectedProvider === 'vertex') {
        if (!vertexCredentials.projectId) {
          setError('Please enter your Google Cloud Project ID');
          return;
        }
        credentials = {
          project_id: vertexCredentials.projectId,
          region: vertexCredentials.region,
        };
      }

      // Use the new backend logic to configure the provider
      await updateProviderSettings(selectedProvider, credentials);

      // Load targets and redirect to first one
      try {
        const targets = await getTargets();
        if (targets.length > 0) {
          const firstTarget = targets[0];
          navigate(`/apis?target=${firstTarget.id}`);
        }
      } catch (err) {
        console.error('Error loading targets:', err);
      }

      await refreshProviders();

      // Complete the onboarding
      onComplete();
    } catch (_err) {
      setError('Failed to configure provider. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const renderWelcomeStep = () => (
    <Box sx={{ textAlign: 'center', py: 4 }}>
      <img src="/logo-white-logotop.svg" alt="legacy-use" style={{ height: '100px' }} />
      <Typography variant="h5" color="text.secondary" sx={{ mt: 3, mb: 2 }}>
        Automate any legacy application with AI
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        legacy-use allows to expose legacy applications with REST-APIs, enabling you to build
        reliable solutions and automate workflows where it was not possible before.
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        To get started, you'll need to configure your AI provider (Anthropic, AWS Bedrock, or Google Vertex).
      </Typography>
      <Box sx={{ mt: 4 }}>
        <Button variant="contained" size="large" onClick={handleNext} startIcon={<KeyIcon />}>
          Configure AI Provider
        </Button>
      </Box>
    </Box>
  );

  const renderProviderStep = () => (
    <Box sx={{ py: 2 }}>
      <Typography variant="h4" component="h2" gutterBottom align="center">
        Configure AI Provider
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph align="center" sx={{ mb: 4 }}>
        Select and configure your preferred AI provider to power legacy-use
      </Typography>

      <FormControl fullWidth sx={{ mb: 3 }}>
        <InputLabel>AI Provider</InputLabel>
        <Select
          value={selectedProvider}
          onChange={e => setSelectedProvider(e.target.value)}
          label="AI Provider"
        >
          {providers
            .filter(provider => provider.provider !== 'legacyuse')
            .map(provider => (
              <MenuItem key={provider.provider} value={provider.provider}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                  }}
                >
                  <Box>
                    <Typography variant="body1">{provider.name}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {provider.description}
                    </Typography>
                  </Box>
                  {provider.available && <Chip label="Configured" color="success" size="small" />}
                </Box>
              </MenuItem>
            ))}
        </Select>
      </FormControl>

      {/* Provider-specific configuration */}
      {selectedProvider === 'anthropic' && (
        <Paper elevation={1} sx={{ p: 3, mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Anthropic Configuration
          </Typography>
          <TextField
            fullWidth
            label="API Key"
            type="password"
            value={apiKeyInput}
            onChange={e => setApiKeyInput(e.target.value)}
            variant="outlined"
            placeholder="Enter your Anthropic API key"
            helperText="You can get your API key from the Anthropic Console"
          />
        </Paper>
      )}

      {selectedProvider === 'bedrock' && (
        <Paper elevation={1} sx={{ p: 3, mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            AWS Bedrock Configuration
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Access Key ID"
                value={awsCredentials.accessKeyId}
                onChange={e =>
                  setAwsCredentials(prev => ({ ...prev, accessKeyId: e.target.value }))
                }
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Secret Access Key"
                type="password"
                value={awsCredentials.secretAccessKey}
                onChange={e =>
                  setAwsCredentials(prev => ({ ...prev, secretAccessKey: e.target.value }))
                }
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Region"
                value={awsCredentials.region}
                onChange={e => setAwsCredentials(prev => ({ ...prev, region: e.target.value }))}
                variant="outlined"
              />
            </Grid>
          </Grid>
        </Paper>
      )}

      {selectedProvider === 'vertex' && (
        <Paper elevation={1} sx={{ p: 3, mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Google Vertex AI Configuration
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Project ID"
                value={vertexCredentials.projectId}
                onChange={e =>
                  setVertexCredentials(prev => ({ ...prev, projectId: e.target.value }))
                }
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Region"
                value={vertexCredentials.region}
                onChange={e => setVertexCredentials(prev => ({ ...prev, region: e.target.value }))}
                variant="outlined"
              />
            </Grid>
          </Grid>
        </Paper>
      )}

      <Button
        fullWidth
        variant="contained"
        size="large"
        onClick={handleProviderSetup}
        disabled={loading}
        sx={{ mt: 2 }}
      >
        {loading ? 'Configuring...' : 'Complete Setup'}
      </Button>
    </Box>
  );

  const renderStepContent = step => {
    switch (step) {
      case 0:
        return renderWelcomeStep();
      case 1:
        return renderProviderStep();
      default:
        return null;
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '80vh' },
      }}
    >
      <DialogContent sx={{ p: 0 }}>
        <Box sx={{ position: 'relative' }}>
          <IconButton
            onClick={onClose}
            sx={{
              position: 'absolute',
              right: 8,
              top: 8,
              zIndex: 1,
            }}
          >
            <CloseIcon />
          </IconButton>

          <Container maxWidth="sm" sx={{ py: 4 }}>
            {/* Stepper */}
            <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 4 }}>
              {steps.map(label => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>

            {/* Error Alert */}
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {/* Step Content */}
            {renderStepContent(activeStep)}

            {/* Navigation */}
            {activeStep > 0 && activeStep < steps.length && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
                <Button onClick={handleBack} disabled={loading}>
                  Back
                </Button>
                <Box /> {/* Spacer */}
              </Box>
            )}
          </Container>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default OnboardingWizard;
