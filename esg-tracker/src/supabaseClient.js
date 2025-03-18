import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://zwfponltzmrnwcgjevik.supabase.co/'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp3ZnBvbmx0em1ybndjZ2pldmlrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIwNzA4NjksImV4cCI6MjA1NzY0Njg2OX0.efK6dWbpOLIlGb-4ORnIYmiiyjg11gCnB1gGquC2lH8'

export const supabase = createClient(supabaseUrl, supabaseKey)
