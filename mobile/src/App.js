import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'expo-status-bar';

import HomeScreen from './screens/HomeScreen';
import BrowserScreen from './screens/BrowserScreen';
import IdentitiesScreen from './screens/IdentitiesScreen';
import SettingsScreen from './screens/SettingsScreen';
import QRScannerScreen from './screens/QRScannerScreen';

import { registerForPushNotifications, addNotificationResponseListener } from './services/notifications';
import { registerBackgroundListener } from './services/backgroundListener';

const Tab = createBottomTabNavigator();
const ConnectStack = createStackNavigator();

// Stack navigator for Connect tab (includes QR scanner)
function ConnectStackNavigator() {
  return (
    <ConnectStack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      <ConnectStack.Screen name="ConnectHome" component={HomeScreen} />
      <ConnectStack.Screen
        name="QRScanner"
        component={QRScannerScreen}
        options={{
          presentation: 'fullScreenModal',
          headerShown: false,
        }}
      />
    </ConnectStack.Navigator>
  );
}

export default function App() {
  useEffect(() => {
    // Initialize push notifications
    async function initNotifications() {
      const token = await registerForPushNotifications();
      if (token) {
        console.log('Push notifications registered');
      }
    }
    initNotifications();

    // Register background listener for incoming connections
    registerBackgroundListener();

    // Handle notification taps
    const subscription = addNotificationResponseListener((response) => {
      const data = response.notification.request.content.data;
      console.log('Notification tapped:', data);
      // Handle navigation based on notification type
      // This could navigate to the connection screen with the code
    });

    return () => {
      subscription.remove();
    };
  }, []);

  return (
    <>
      <StatusBar style="auto" />
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={{
            tabBarActiveTintColor: '#4299E1',
            tabBarInactiveTintColor: '#A0AEC0',
            headerStyle: {
              backgroundColor: '#fff',
            },
            headerTintColor: '#2D3748',
            headerTitleStyle: {
              fontWeight: '600',
            },
          }}
        >
          <Tab.Screen
            name="Connect"
            component={ConnectStackNavigator}
            options={{
              title: 'Connect',
              tabBarLabel: 'Connect',
              headerTitle: 'Wormhole',
            }}
          />
          <Tab.Screen
            name="Browser"
            component={BrowserScreen}
            options={{
              title: 'Browser',
              tabBarLabel: 'Browser',
              headerTitle: 'WNS Browser',
            }}
          />
          <Tab.Screen
            name="Identities"
            component={IdentitiesScreen}
            options={{
              title: 'Identities',
              tabBarLabel: 'Identities',
              headerTitle: 'My Identities',
            }}
          />
          <Tab.Screen
            name="Settings"
            component={SettingsScreen}
            options={{
              title: 'Settings',
              tabBarLabel: 'Settings',
              headerTitle: 'Settings',
            }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </>
  );
}
