import AddIcon from '@mui/icons-material/Add';
import VisibilityIcon from '@mui/icons-material/Visibility';
import {
  Box,
  Button,
  Chip,
  List,
  ListItem,
  ListItemSecondaryAction,
  ListItemText,
  Paper,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

const JobsSection = ({
  jobs,
  blockingJobs,
  queuedJobs,
  executedJobs,
  queueStatus,
  activeTab,
  setActiveTab,
  targetId,
  selectedSession,
  setSelectedSessionId,
  formatDate,
  getStatusColor,
}) => (
  <Box sx={{ mb: 4 }}>
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
      <Typography variant="h5">Jobs</Typography>
      <Tooltip title="Add Job">
        <Button
          variant="contained"
          color="primary"
          component={RouterLink}
          to={`/apis?targetId=${targetId}${selectedSession ? `&sessionId=${selectedSession.id}` : ''}`}
          onClick={() => setSelectedSessionId(selectedSession?.id)}
          size="small"
        >
          <AddIcon />
        </Button>
      </Tooltip>
    </Box>
    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
      <Tabs value={activeTab} onChange={(_e, newValue) => setActiveTab(newValue)}>
        <Tab label="All Jobs" />
        <Tab
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <span>Blocking</span>
              {blockingJobs.length > 0 && (
                <Chip label={blockingJobs.length} size="small" color="error" sx={{ ml: 1 }} />
              )}
            </Box>
          }
        />
        <Tab
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <span>Queued</span>
              {queuedJobs.length > 0 && (
                <Chip label={queuedJobs.length} size="small" color="primary" sx={{ ml: 1 }} />
              )}
            </Box>
          }
        />
        <Tab label="Executed" />
      </Tabs>
    </Box>
    {activeTab === 0 &&
      (jobs.length > 0 ? (
        <List component={Paper}>
          {jobs.map(job => (
            <ListItem key={job.id} divider>
              <ListItemText
                primary={job.api_name}
                secondary={
                  <Box component="span">
                    <Typography component="span" variant="body2" color="textSecondary">
                      Created: {formatDate(job.created_at)}
                    </Typography>
                    <br />
                    <Chip
                      label={job.status}
                      size="small"
                      color={getStatusColor(job.status)}
                      sx={{ mt: 1 }}
                    />
                  </Box>
                }
                secondaryTypographyProps={{ component: 'div' }}
              />
              <ListItemSecondaryAction>
                <Tooltip title="View Job Details">
                  <Button component={RouterLink} to={`/jobs/${targetId}/${job.id}`} size="small">
                    <VisibilityIcon />
                  </Button>
                </Tooltip>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1">No jobs found for this target</Typography>
        </Paper>
      ))}
    {activeTab === 1 &&
      (blockingJobs.length > 0 ? (
        <>
          <Typography variant="subtitle1" gutterBottom>
            Blocking Jobs:
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'error.light', color: 'error.contrastText' }}>
            <Typography variant="body2">
              These jobs are blocking the execution of new jobs. Resolve or cancel them to allow
              queue processing to continue.
            </Typography>
          </Paper>
          <List component={Paper}>
            {blockingJobs.map(job => (
              <ListItem key={job.id} divider>
                <ListItemText
                  primary={job.api_name}
                  secondary={
                    <>
                      <Typography component="span" variant="body2" color="textSecondary">
                        Created: {formatDate(job.created_at)}
                      </Typography>
                      <br />
                      <Chip
                        label={job.status}
                        size="small"
                        color={getStatusColor(job.status)}
                        sx={{ mt: 1 }}
                      />
                    </>
                  }
                />
                <ListItemSecondaryAction>
                  <Tooltip title="View Job Details">
                    <Button component={RouterLink} to={`/jobs/${targetId}/${job.id}`} size="small">
                      <VisibilityIcon />
                    </Button>
                  </Tooltip>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1">No blocking jobs found</Typography>
        </Paper>
      ))}
    {activeTab === 2 &&
      (queuedJobs.length > 0 ? (
        <>
          {queueStatus?.running_job && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Currently Running:
              </Typography>
              <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                <Typography variant="body1">{queueStatus.running_job.api_name}</Typography>
                <Chip label="RUNNING" size="small" color="warning" sx={{ mt: 1 }} />
              </Paper>
            </Box>
          )}
          <Typography variant="subtitle1" gutterBottom>
            In Queue:
          </Typography>
          <List component={Paper}>
            {queuedJobs.map(job => (
              <ListItem key={job.id} divider>
                <ListItemText
                  primary={job.api_name}
                  secondary={
                    <>
                      <Typography component="span" variant="body2" color="textSecondary">
                        Created: {formatDate(job.created_at)}
                      </Typography>
                      <br />
                      <Chip
                        label={job.status}
                        size="small"
                        color={getStatusColor(job.status)}
                        sx={{ mt: 1 }}
                      />
                    </>
                  }
                />
                <ListItemSecondaryAction>
                  <Tooltip title="View Job Details">
                    <Button component={RouterLink} to={`/jobs/${targetId}/${job.id}`} size="small">
                      <VisibilityIcon />
                    </Button>
                  </Tooltip>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1">No jobs in queue</Typography>
        </Paper>
      ))}
    {activeTab === 3 &&
      (executedJobs.length > 0 ? (
        <List component={Paper}>
          {executedJobs.map(job => (
            <ListItem key={job.id} divider>
              <ListItemText
                primary={job.api_name}
                secondary={
                  <Box component="span">
                    <Typography component="span" variant="body2" color="textSecondary">
                      Created: {formatDate(job.created_at)}
                    </Typography>
                    <br />
                    <Chip
                      label={job.status}
                      size="small"
                      color={getStatusColor(job.status)}
                      sx={{ mt: 1 }}
                    />
                  </Box>
                }
                secondaryTypographyProps={{ component: 'div' }}
              />
              <ListItemSecondaryAction>
                <Tooltip title="View Job Details">
                  <Button component={RouterLink} to={`/jobs/${targetId}/${job.id}`} size="small">
                    <VisibilityIcon />
                  </Button>
                </Tooltip>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1">No executed jobs found</Typography>
        </Paper>
      ))}
  </Box>
);

export default JobsSection;
